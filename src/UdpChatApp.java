import javax.swing.*;
import java.awt.*;
import java.net.*;
import java.nio.charset.StandardCharsets;

public class UdpChatApp extends JFrame {
    private final JComboBox<String> modeBox =
            new JComboBox<>(new String[]{"Unicast", "Broadcast", "Multicast"});
    private final JTextField ipField = new JTextField("127.0.0.1");
    private final JTextField portField = new JTextField("5000");
    private final JTextField multicastField = new JTextField("239.0.0.1");
    private final JTextField messageField = new JTextField();
    private final JTextArea logArea = new JTextArea();
    private final JLabel status = new JLabel("Chưa kết nối");
    private DatagramSocket socket;
    private MulticastSocket multicastSocket;
    private volatile boolean running;

    public UdpChatApp() {
        super("UDP Communication - Unicast / Broadcast / Multicast");
        setDefaultCloseOperation(EXIT_ON_CLOSE);
        setSize(760, 560);
        setLocationRelativeTo(null);
        buildUi();
        modeBox.addActionListener(e -> updateFields());
        updateFields();
    }
    private void buildUi() {
        JPanel config = new JPanel(new GridLayout(4, 4, 8, 8));
        config.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));
        config.add(new JLabel("Chế độ:"));
        config.add(modeBox);
        config.add(new JLabel("IP đích / Broadcast:"));
        config.add(ipField);
        config.add(new JLabel("Port:"));
        config.add(portField);
        config.add(new JLabel("Multicast Group:"));
        config.add(multicastField);
        JButton start = new JButton("Bắt đầu nhận");
        JButton stop = new JButton("Dừng nhận");
        JButton send = new JButton("Gửi");
        config.add(start);
        config.add(stop);
        config.add(send);
        config.add(status);
        add(config, BorderLayout.NORTH);

        logArea.setEditable(false);
        logArea.setLineWrap(true);
        add(new JScrollPane(logArea), BorderLayout.CENTER);

        JPanel bottom = new JPanel(new BorderLayout(8, 8));
        bottom.setBorder(BorderFactory.createEmptyBorder(8, 10, 10, 10));
        bottom.add(new JLabel("Tin nhắn:"), BorderLayout.WEST);
        bottom.add(messageField, BorderLayout.CENTER);        add(bottom, BorderLayout.SOUTH);

        start.addActionListener(e -> startReceiver());
        stop.addActionListener(e -> stopReceiver());
        send.addActionListener(e -> sendMessage());
        messageField.addActionListener(e -> sendMessage());
    }

    private void updateFields() {
        boolean multicast = modeBox.getSelectedItem().equals("Multicast");
        multicastField.setEnabled(multicast);
    }

    private int getPort() {
        int port = Integer.parseInt(portField.getText().trim());
        if (port < 1 || port > 65535) {
            throw new IllegalArgumentException("Port phải từ 1 đến 65535.");
        }
        return port;
    }

    private void startReceiver() {
        stopReceiver();
        try {
            int port = getPort();
            String mode = (String) modeBox.getSelectedItem();
            running = true;
            if ("Multicast".equals(mode)) {                InetAddress group = InetAddress.getByName(multicastField.getText().trim());
                multicastSocket = new MulticastSocket(port);
                multicastSocket.joinGroup(group);
                status.setText("Đang nhận Multicast");
                append("Đã join group " + group.getHostAddress() + ":" + port);
                new Thread(() -> receiveMulticast(group), "multicast-receiver").start();
            } else {
                socket = new DatagramSocket(port);
                status.setText("Đang nhận " + mode);
                append("Đang lắng nghe UDP port " + port);
                new Thread(this::receiveNormal, "udp-receiver").start();
            }
        } catch (Exception ex) {
            running = false;
            showError(ex);
        }
    }

    private void receiveNormal() {
        byte[] buffer = new byte[65507];
        while (running && socket != null) {
            try {
                DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
                socket.receive(packet);
                append("[" + packet.getAddress().getHostAddress() + ":" + packet.getPort()
                        + "] " + new String(packet.getData(), packet.getOffset(),
                        packet.getLength(), StandardCharsets.UTF_8));
            } catch (Exception ex) {                if (running) append("Lỗi nhận: " + ex.getMessage());
            }
        }
    }

    private void receiveMulticast(InetAddress group) {
        byte[] buffer = new byte[65507];
        while (running && multicastSocket != null) {
            try {
                DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
                multicastSocket.receive(packet);
                append("[Multicast " + group.getHostAddress() + "] "
                        + new String(packet.getData(), packet.getOffset(),
                        packet.getLength(), StandardCharsets.UTF_8));
            } catch (Exception ex) {
                if (running) append("Lỗi Multicast: " + ex.getMessage());
            }
        }
    }

    private void sendMessage() {
        String text = messageField.getText().trim();
        if (text.isEmpty()) return;
        try {
            int port = getPort();
            String mode = (String) modeBox.getSelectedItem();
            String address = "Multicast".equals(mode)
                    ? multicastField.getText().trim()                    : ipField.getText().trim();
            InetAddress target = InetAddress.getByName(address);
            byte[] data = text.getBytes(StandardCharsets.UTF_8);
            DatagramSocket sender = new DatagramSocket();
            if ("Broadcast".equals(mode)) sender.setBroadcast(true);
            sender.send(new DatagramPacket(data, data.length, target, port));
            sender.close();
            append("[Gửi " + mode + "] " + address + ":" + port + " -> " + text);
            messageField.setText("");
        } catch (Exception ex) {
            showError(ex);
        }
    }

    private void stopReceiver() {
        running = false;
        try {
            if (multicastSocket != null) {
                multicastSocket.close();
                multicastSocket = null;
            }
            if (socket != null) {
                socket.close();
                socket = null;
            }
        } finally {
            status.setText("Đã dừng nhận");
        }    }

    private void append(String text) {
        SwingUtilities.invokeLater(() ->
                logArea.append(text + System.lineSeparator()));
    }

    private void showError(Exception ex) {
        append("ERROR: " + ex.getMessage());
        JOptionPane.showMessageDialog(
                this, ex.getMessage(), "Lỗi", JOptionPane.ERROR_MESSAGE);
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() ->
                new UdpChatApp().setVisible(true));
    }
}
