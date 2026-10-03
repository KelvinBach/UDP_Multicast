# UDP Multicast Chat

Ứng dụng chat sử dụng **Java UDP** với giao diện **React**.

## Chức năng

- **Unicast**: gửi đến một máy cụ thể.
- **Broadcast**: gửi đến các thiết bị trong phạm vi broadcast của mạng.
- **Multicast**: gửi đến một nhóm người dùng.
- Đặt **Nickname** và **Group Name**.
- Cấu hình IP đích, Broadcast IP, Port và Multicast Group.
- Gửi bằng nút **Gửi** hoặc phím **Enter**.
- Hiển thị trạng thái, IP cục bộ, nickname, địa chỉ và thời gian tin nhắn.

## Công nghệ

Frontend: React, Vite, JavaScript, HTML/CSS.

Backend: Java, UDP Socket, Java HTTP Server.

Kiến trúc:

~~~text
React UI
   |
   | HTTP API
   v
UdpChatServer.java
   |
   +---- Unicast UDP
   +---- Broadcast UDP
   +---- Multicast UDP
~~~

## Yêu cầu

Cài đặt:

- JDK 17 trở lên
- Node.js 18 trở lên
- npm

Kiểm tra:

~~~powershell
java -version
javac -version
node --version
npm --version
~~~

## Cấu trúc thư mục

~~~text
UDP_Multicast/
├── backend/
│   ├── UdpChatServer.java
│   └── bin/
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── dist/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   └── index.html
├── src/
│   └── UdpChatApp.java
└── README.md
~~~

## Chạy lần đầu

Mở PowerShell tại thư mục project:

~~~powershell
cd "D:\Documents\Lap_trinh_ung_dung_mang\Tuan03\UDP_Multicast"
~~~

### 1. Cài dependency React

~~~powershell
cd frontend
npm install
~~~

### 2. Build React

~~~powershell
npm run build
cd ..
~~~

Sau khi build phải có thư mục frontend/dist/.

### 3. Compile Java

~~~powershell
New-Item -ItemType Directory -Force backend\bin
javac -encoding UTF-8 -d backend\bin backend\UdpChatServer.java
~~~

### 4. Chạy server

~~~powershell
java -cp backend\bin UdpChatServer
~~~

Nếu thành công sẽ thấy tương tự:

~~~text
UDP Chat server: http://0.0.0.0:8080
Local address: 192.168.x.x
~~~

## Mở giao diện

Trên máy chạy server:

~~~text
http://localhost:8080
~~~

Hoặc:

~~~text
http://127.0.0.1:8080
~~~

Máy khác trong cùng mạng có thể truy cập:

~~~text
http://IP-MAY-CHAY-SERVER:8080
~~~

Ví dụ:

~~~text
http://192.168.1.10:8080
~~~

## Cấu hình giao diện

### Nickname

Nhập tên muốn hiển thị, ví dụ:

~~~text
Alice
~~~

### Group Name

Nhập tên nhóm, ví dụ:

~~~text
TeamChat
~~~

### Port

Mặc định là 5000. Các máy cần giao tiếp nên dùng cùng UDP port nhận.

## Test Unicast

Mô hình:

~~~text
Laptop A  -------- UDP -------->  Laptop B
~~~

Ví dụ Laptop A có IP 192.168.1.10, Laptop B có IP 192.168.1.20.

Laptop A:

~~~text
Nickname: Alice
Mode: Unicast
IP đích: 192.168.1.20
Port: 5000
~~~

Laptop B:

~~~text
Nickname: Bob
Mode: Unicast
IP đích: 192.168.1.10
Port: 5000
~~~

Trên cả hai máy:

1. Nhấn **Bắt đầu nhận**.
2. Nhập tin nhắn.
3. Nhấn **Gửi**.

## Test Broadcast

Trên Windows:

~~~powershell
ipconfig
~~~

Ví dụ:

~~~text
IPv4:       192.168.1.10
Subnet:     255.255.255.0
Broadcast:  192.168.1.255
~~~

Trong giao diện:

~~~text
Mode: Broadcast
IP Broadcast: 192.168.1.255
Port: 5000
~~~

Không mặc định dùng 192.168.1.255 cho mọi mạng. Broadcast IP phải phù hợp với subnet thực tế.

## Test Multicast

Ví dụ:

~~~text
Multicast Group: 239.0.0.1
Port: 5000
Group Name: TeamChat
~~~

Các máy tham gia nhóm phải dùng cùng Multicast Group và Port.

Sau đó chọn **Multicast** và nhấn **Bắt đầu nhận**.

## Chạy trên hai laptop

### Laptop A

Lấy IP:

~~~powershell
ipconfig
~~~

Ví dụ:

~~~text
192.168.1.10
~~~

Chạy:

~~~powershell
java -cp backend\bin UdpChatServer
~~~

### Laptop B

Nếu Laptop B có source project, cũng chạy:

~~~powershell
java -cp backend\bin UdpChatServer
~~~

Mở giao diện trên mỗi máy:

~~~text
http://localhost:8080
~~~

Nếu chỉ muốn Laptop B dùng server của Laptop A:

~~~text
http://192.168.1.10:8080
~~~

## Kiểm tra kết nối giữa hai laptop

Trên A:

~~~powershell
ping 192.168.1.20
~~~

Trên B:

~~~powershell
ping 192.168.1.10
~~~

Nếu ping không được, kiểm tra:

1. Hai máy có thực sự cùng mạng LAN/Wi-Fi không.
2. IPv4 và Subnet Mask.
3. Network Profile có phải **Private** không.
4. Windows Firewall.
5. Router có bật AP Isolation / Client Isolation không.

Ping sử dụng ICMP, còn ứng dụng sử dụng UDP. Vì vậy ping không phải là bài kiểm tra UDP trực tiếp, nhưng ping không được thường là dấu hiệu cần kiểm tra cấu hình mạng.

## Windows Firewall

Khi test giữa hai laptop, cần kiểm tra:

- TCP 8080: giao diện/API.
- UDP 5000: UDP chat.
- ICMP: ping.

Không nên tắt Firewall lâu dài. Nên tạo rule cho đúng port cần dùng.

## React development mode

Khi muốn phát triển giao diện với Vite:

~~~powershell
cd frontend
npm run dev
~~~

Mở:

~~~text
http://localhost:5173
~~~

Development mode sử dụng proxy:

~~~text
React :5173
   |
   v
Java API :8080
~~~

Sau khi hoàn thành:

~~~powershell
npm run build
~~~

Sau đó chạy Java server và dùng:

~~~text
http://localhost:8080
~~~

## API chính

| API | Method | Chức năng |
|---|---|---|
| /api/state | GET | Lấy trạng thái và tin nhắn |
| /api/start | POST | Bắt đầu nhận UDP |
| /api/stop | POST | Dừng nhận UDP |
| /api/send | POST | Gửi UDP |

## Lỗi thường gặp

### Address already in use

Port đang được chương trình khác sử dụng.

~~~powershell
netstat -ano | findstr :8080
netstat -ano | findstr :5000
~~~

### Không mở được localhost:8080

Kiểm tra Java server có đang chạy và có dòng:

~~~text
UDP Chat server: http://0.0.0.0:8080
~~~

### Unicast không nhận

Kiểm tra IP đích, UDP port, trạng thái Bắt đầu nhận và Firewall.

### Broadcast không nhận

Kiểm tra Broadcast IP, Subnet, Firewall và Wi-Fi/router có chặn broadcast hay không.

### Multicast không nhận

Kiểm tra Multicast Group, Port, card mạng, Firewall và Wi-Fi/router có chặn multicast hay không.

## Lệnh chạy nhanh

~~~powershell
cd "D:\Documents\Lap_trinh_ung_dung_mang\Tuan03\UDP_Multicast"

cd frontend
npm install
npm run build
cd ..

New-Item -ItemType Directory -Force backend\bin
javac -encoding UTF-8 -d backend\bin backend\UdpChatServer.java

java -cp backend\bin UdpChatServer
~~~

Sau đó mở:

~~~text
http://localhost:8080
~~~

## Quy trình test đề xuất

~~~text
1. Chạy trên 1 máy
        ↓
2. Test Unicast localhost
        ↓
3. Test Unicast giữa 2 laptop
        ↓
4. Test Broadcast
        ↓
5. Test Multicast
~~~

Nếu Unicast giữa hai laptop chưa hoạt động, nên xử lý mạng và Firewall trước khi chuyển sang Broadcast/Multicast.

## Ghi chú

- UDP không đảm bảo gói tin đến nơi, đúng thứ tự hoặc không bị mất.
- Broadcast phụ thuộc vào cấu hình mạng.
- Multicast phụ thuộc vào khả năng hỗ trợ multicast của mạng.
- UDP chat mặc định sử dụng port 5000.
- HTTP/API mặc định sử dụng port 8080.
- Có thể thay đổi UDP port trực tiếp trên giao diện.
