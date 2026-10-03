import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

public class UdpChatServer {
    private static final int HTTP_PORT = 8081;
    private static final String SEP = "\u001F";
    private static final Path WEB_ROOT = Paths.get("frontend", "dist").toAbsolutePath();
    private static final DateTimeFormatter TIME = DateTimeFormatter.ofPattern("HH:mm:ss");
    private static final List<Message> messages = new CopyOnWriteArrayList<>();
    private static final Set<String> sentIds = ConcurrentHashMap.newKeySet();
    private static final AtomicLong sequence = new AtomicLong();
    private static volatile DatagramSocket socket;
    private static volatile MulticastSocket multicastSocket;
    private static volatile NetworkInterface multicastInterface;
    private static volatile boolean running;
    private static volatile Config config = new Config();
    private static String localAddress = "127.0.0.1";

    public static void main(String[] args) throws Exception {
        localAddress = detectLocalAddress();
        HttpServer server = HttpServer.create(new InetSocketAddress("0.0.0.0", HTTP_PORT), 0);
        server.createContext("/api/state", UdpChatServer::state);
        server.createContext("/api/network", UdpChatServer::network);
        server.createContext("/api/start", UdpChatServer::start);
        server.createContext("/api/stop", UdpChatServer::stop);
        server.createContext("/api/send", UdpChatServer::send);
        server.createContext("/", UdpChatServer::staticFile);
        server.setExecutor(Executors.newCachedThreadPool());
        server.start();
        System.out.println("UDP Chat server: http://0.0.0.0:" + HTTP_PORT);
        System.out.println("Local address: " + localAddress);
    }

    private static void start(HttpExchange ex) throws IOException {
        if (!"POST".equalsIgnoreCase(ex.getRequestMethod())) {
            json(ex, 405, "{\"error\":\"Method not allowed\"}");
            return;
        }
        try {
            Map<String,String> q = query(ex.getRequestURI().getRawQuery());
            Config next = Config.from(q);
            stopUdp();
            config = next;
            startUdp(next);
            json(ex, 200, "{\"running\":true}");
        } catch (Exception e) {
            json(ex, 400, "{\"error\":"+quote(e.getMessage())+"}");
        }
    }

    private static void stop(HttpExchange ex) throws IOException {
        stopUdp();
        json(ex, 200, "{\"running\":false}");
    }

    private static void send(HttpExchange ex) throws IOException {
        if (!"POST".equalsIgnoreCase(ex.getRequestMethod())) {
            json(ex, 405, "{\"error\":\"Method not allowed\"}");
            return;
        }
        try {
            Map<String,String> q = query(new String(ex.getRequestBody().readAllBytes(),
                    StandardCharsets.UTF_8));
            Config next = Config.from(q);
            String text = q.getOrDefault("message", "").trim();
            if (text.isEmpty()) throw new IllegalArgumentException("Tin nhắn không được để trống.");
            sendUdp(next, text);
            addMessage(next.nickname, localAddress, next.groupName, text, true);
            json(ex, 200, "{\"sent\":true}");
        } catch (Exception e) {
            json(ex, 400, "{\"error\":"+quote(e.getMessage())+"}");
        }
    }
    private static void network(HttpExchange ex) throws IOException {
        try {
            NetworkConfig n = detectNetworkConfig();
            json(ex, 200, n.toJson());
        } catch (Exception e) {
            json(ex, 500, "{\"error\":"+quote(e.getMessage())+"}");
        }
    }

    private static void state(HttpExchange ex) throws IOException {
        StringBuilder out = new StringBuilder();
        out.append("{\"running\":").append(running);
        out.append(",\"localAddress\":").append(quote(localAddress));
        out.append(",\"messages\":[");
        boolean first = true;
        for (Message m : messages) {
            if (!first) out.append(",");
            first = false;
            out.append(m.toJson());
        }
        out.append("]}");
        json(ex, 200, out.toString());
    }

    private static void startUdp(Config c) throws Exception {
        int port = c.port;
        if ("Multicast".equals(c.mode)) {
            InetAddress group = InetAddress.getByName(c.group);
            if (!group.isMulticastAddress()) {
                throw new IllegalArgumentException("Multicast Group không hợp lệ.");
            }
            multicastSocket = new MulticastSocket(port);
            NetworkInterface ni = findMulticastInterface();
            if (ni == null) {
                multicastSocket.close();
                multicastSocket = null;
                throw new IllegalStateException("Không tìm thấy card mạng hỗ trợ Multicast.");
            }
            multicastInterface = ni;
            multicastSocket.setNetworkInterface(ni);
            multicastSocket.joinGroup(new InetSocketAddress(group, port), ni);
            running = true;
            Thread t = new Thread(() -> receiveMulticast(group), "udp-multicast-receiver");
            t.start();
        } else {
            socket = new DatagramSocket(port);
            running = true;
            Thread t = new Thread(UdpChatServer::receiveNormal, "udp-receiver");
            t.start();
        }
    }

    private static void receiveNormal() {
        byte[] buffer = new byte[65507];
        while (running && socket != null) {
            try {
                DatagramPacket p = new DatagramPacket(buffer, buffer.length);
                socket.receive(p);
                handlePacket(p);
            } catch (Exception e) {
                if (running) System.err.println("UDP receive: " + e.getMessage());
            }
        }
    }

    private static void receiveMulticast(InetAddress group) {
        byte[] buffer = new byte[65507];
        while (running && multicastSocket != null) {
            try {
                DatagramPacket p = new DatagramPacket(buffer, buffer.length);
                multicastSocket.receive(p);
                handlePacket(p);
            } catch (Exception e) {
                if (running) System.err.println("Multicast receive: " + e.getMessage());
            }
        }
    }

    private static void handlePacket(DatagramPacket p) {
        String raw = new String(p.getData(), p.getOffset(), p.getLength(), StandardCharsets.UTF_8);
        String[] parts = raw.split(SEP, 4);
        String id = parts.length == 4 ? parts[0] : "";
        if (!id.isEmpty() && sentIds.remove(id)) return;
        String nickname = parts.length == 4 ? parts[1] : "Người dùng";
        String groupName = parts.length == 4 ? parts[2] : config.groupName;
        String text = parts.length == 4 ? parts[3] : raw;
        addMessage(nickname, p.getAddress().getHostAddress() + ":" + p.getPort(),
                groupName, text, false);
    }

    private static void sendUdp(Config c, String text) throws Exception {
        InetAddress target = InetAddress.getByName(
                "Multicast".equals(c.mode) ? c.group : c.ip);
        String id = UUID.randomUUID().toString();
        sentIds.add(id);
        byte[] data = (id + SEP + clean(c.nickname) + SEP
                + clean(c.groupName) + SEP + text).getBytes(StandardCharsets.UTF_8);
        if ("Multicast".equals(c.mode)) {
            NetworkInterface ni = multicastInterface;
            if (ni == null) ni = findMulticastInterface();
            if (ni == null) throw new IllegalStateException("Không tìm thấy card mạng Multicast để gửi.");

            // Windows/JDK hiện tại có thể từ chối IP_MULTICAST_IF trên socket gửi
            // với lỗi "Invalid argument: setsockopt". Để hệ điều hành chọn
            // interface theo routing table; socket nhận vẫn được bind vào Wi-Fi cụ thể.
            MulticastSocket sender = new MulticastSocket();
            sender.setTimeToLive(1);
            sender.send(new DatagramPacket(data, data.length, target, c.port));
            sender.close();
        } else {
            DatagramSocket sender = new DatagramSocket();
            if ("Broadcast".equals(c.mode)) sender.setBroadcast(true);
            sender.send(new DatagramPacket(data, data.length, target, c.port));
            sender.close();
        }
    }

    private static void stopUdp() {
        running = false;
        if (multicastSocket != null) {
            multicastSocket.close();
            multicastSocket = null;
        }
        multicastInterface = null;
        if (socket != null) {
            socket.close();
            socket = null;
        }
    }
    private static void addMessage(String nickname, String address,
                                    String groupName, String text, boolean own) {
        Message m = new Message(sequence.incrementAndGet(), nickname, address,
                groupName, text, TIME.format(LocalTime.now()), own);
        messages.add(m);
        while (messages.size() > 200) messages.remove(0);
    }

    private static NetworkInterface findMulticastInterface() throws SocketException {
        Enumeration<NetworkInterface> all = NetworkInterface.getNetworkInterfaces();
        NetworkInterface fallback = null;
        while (all.hasMoreElements()) {
            NetworkInterface ni = all.nextElement();
            if (!ni.isUp() || ni.isLoopback() || !ni.supportsMulticast()) continue;
            if (hasAddress(ni, localAddress)) return ni;
            if (fallback == null) fallback = ni;
        }
        return fallback;
    }

    private static boolean hasAddress(NetworkInterface ni, String address) {
        Enumeration<InetAddress> addresses = ni.getInetAddresses();
        while (addresses.hasMoreElements()) {
            if (address.equals(addresses.nextElement().getHostAddress())) return true;
        }
        return false;
    }

    private static NetworkConfig detectNetworkConfig() throws SocketException {
        Enumeration<NetworkInterface> all = NetworkInterface.getNetworkInterfaces();
        NetworkConfig fallback = null;
        while (all.hasMoreElements()) {
            NetworkInterface ni = all.nextElement();
            if (!ni.isUp() || ni.isLoopback() || !ni.supportsMulticast()) continue;
            for (InterfaceAddress ia : ni.getInterfaceAddresses()) {
                InetAddress a = ia.getAddress();
                if (!(a instanceof Inet4Address) || a.isLoopbackAddress()) continue;
                String ip = a.getHostAddress();
                String broadcast = ia.getBroadcast() == null ? "" : ia.getBroadcast().getHostAddress();
                int prefix = ia.getNetworkPrefixLength();
                NetworkConfig n = new NetworkConfig(ip, broadcast, prefix, ni.getDisplayName());
                if (broadcast != null && !broadcast.isEmpty()) return n;
                if (fallback == null) fallback = n;
            }
        }
        if (fallback != null) return fallback;
        return new NetworkConfig("127.0.0.1", "255.255.255.255", 8, "Loopback");
    }

    private static String detectLocalAddress() {
        try {
            Enumeration<NetworkInterface> all = NetworkInterface.getNetworkInterfaces();
            while (all.hasMoreElements()) {
                NetworkInterface ni = all.nextElement();
                if (!ni.isUp() || ni.isLoopback()) continue;
                Enumeration<InetAddress> addresses = ni.getInetAddresses();
                while (addresses.hasMoreElements()) {
                    InetAddress a = addresses.nextElement();
                    if (a instanceof Inet4Address && !a.isLoopbackAddress())
                        return a.getHostAddress();
                }
            }
        } catch (Exception ignored) {
        }
        return "127.0.0.1";
    }

    private static void staticFile(HttpExchange ex) throws IOException {
        String request = ex.getRequestURI().getPath();
        if (request.equals("/")) request = "/index.html";
        Path file = WEB_ROOT.resolve(request.substring(1)).normalize();
        if (!file.startsWith(WEB_ROOT) || !Files.isRegularFile(file)) {
            json(ex, 404, "{\"error\":\"Không tìm thấy tài nguyên.\"}");
            return;
        }
        String type = contentType(file);
        byte[] bytes = Files.readAllBytes(file);
        ex.getResponseHeaders().set("Content-Type", type);
        ex.sendResponseHeaders(200, bytes.length);
        try (OutputStream out = ex.getResponseBody()) {
            out.write(bytes);
        }
    }

    private static String contentType(Path file) {
        String n = file.getFileName().toString().toLowerCase(Locale.ROOT);
        if (n.endsWith(".html")) return "text/html; charset=UTF-8";
        if (n.endsWith(".js")) return "text/javascript; charset=UTF-8";
        if (n.endsWith(".css")) return "text/css; charset=UTF-8";
        if (n.endsWith(".svg")) return "image/svg+xml";
        if (n.endsWith(".png")) return "image/png";
        return "application/octet-stream";
    }

    private static Map<String,String> query(String raw) {
        Map<String,String> map = new HashMap<>();
        if (raw == null || raw.isEmpty()) return map;
        for (String item : raw.split("&")) {
            String[] pair = item.split("=", 2);
            String key = decode(pair[0]);
            String value = pair.length > 1 ? decode(pair[1]) : "";
            map.put(key, value);
        }
        return map;
    }

    private static String decode(String value) {
        try { return URLDecoder.decode(value, StandardCharsets.UTF_8); }
        catch (Exception e) { return value; }
    }

    private static String clean(String value) {
        return value == null ? "" : value.replace(SEP, " ");
    }

    private static String quote(String value) {
        if (value == null) value = "Unknown error";
        return "\""
                + value.replace("\\", "\\\\").replace("\"", "\\\"")
                .replace("\n", "\\n").replace("\r", "\\r")
                + "\"";
    }
    private static void json(HttpExchange ex, int status, String body) throws IOException {
        byte[] data = body.getBytes(StandardCharsets.UTF_8);
        ex.getResponseHeaders().set("Content-Type", "application/json; charset=UTF-8");
        ex.getResponseHeaders().set("Access-Control-Allow-Origin", "*");
        ex.getResponseHeaders().set("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
        ex.getResponseHeaders().set("Access-Control-Allow-Headers", "Content-Type");
        ex.sendResponseHeaders(status, data.length);
        try (OutputStream out = ex.getResponseBody()) {
            out.write(data);
        }
    }

    private record NetworkConfig(String localAddress, String broadcastAddress,
                                  int prefixLength, String interfaceName) {
        String toJson() {
            return "{"
                    + "\"localAddress\":" + quote(localAddress)
                    + ",\"broadcastAddress\":" + quote(broadcastAddress)
                    + ",\"prefixLength\":" + prefixLength
                    + ",\"interfaceName\":" + quote(interfaceName)
                    + "}";
        }
    }

    private static class Config {
        String mode = "Unicast";
        String ip = "127.0.0.1";
        int port = 5000;
        String group = "239.0.0.1";
        String groupName = "TeamChat";
        String nickname = "User01";

        static Config from(Map<String,String> q) {
            Config c = new Config();
            c.mode = q.getOrDefault("mode", c.mode);
            c.ip = q.getOrDefault("ip", c.ip);
            c.group = q.getOrDefault("group", c.group);
            c.groupName = q.getOrDefault("groupName", c.groupName).trim();
            c.nickname = q.getOrDefault("nickname", c.nickname).trim();
            c.port = Integer.parseInt(q.getOrDefault("port", "5000"));
            if (c.port < 1 || c.port > 65535)
                throw new IllegalArgumentException("Port phải từ 1 đến 65535.");
            if (c.nickname.isEmpty()) c.nickname = "User01";
            if (c.groupName.isEmpty()) c.groupName = "TeamChat";
            if (!c.mode.equals("Unicast") && !c.mode.equals("Broadcast")
                    && !c.mode.equals("Multicast"))
                throw new IllegalArgumentException("Chế độ truyền không hợp lệ.");
            return c;
        }
    }

    private record Message(long id, String nickname, String address,
                           String groupName, String message, String time, boolean own) {
        String toJson() {
            return "{\"id\":" + id
                    + ",\"nickname\":" + quote(nickname)
                    + ",\"address\":" + quote(address)
                    + ",\"groupName\":" + quote(groupName)
                    + ",\"message\":" + quote(message)
                    + ",\"time\":" + quote(time)
                    + ",\"own\":" + own + "}";
        }
    }
}
