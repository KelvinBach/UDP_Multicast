import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const modes = [
  { id: "Unicast", icon: "◎", label: "Unicast" },
  { id: "Broadcast", icon: "◉", label: "Broadcast" },
  { id: "Multicast", icon: "◌", label: "Multicast" }
];

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Có lỗi kết nối máy chủ");
  return data;
}

function App() {
  const [nickname, setNickname] = useState("User01");
  const [mode, setMode] = useState("Unicast");
  const [ip, setIp] = useState("127.0.0.1");
  const [broadcastAddress, setBroadcastAddress] = useState("");
  const [networkInfo, setNetworkInfo] = useState(null);
  const [port, setPort] = useState("5000");
  const [group, setGroup] = useState("239.0.0.1");
  const [groupName, setGroupName] = useState("TeamChat");
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [running, setRunning] = useState(false);
  const [localAddress, setLocalAddress] = useState("Đang lấy địa chỉ...");
  const [error, setError] = useState("");
  const chatRef = useRef(null);

  const activeTarget = useMemo(
    () => mode === "Multicast" ? group : mode === "Broadcast" ? broadcastAddress : ip,
    [mode, group, ip, broadcastAddress]
  );

  useEffect(() => {
    api("/api/network")
      .then(data => {
        setNetworkInfo(data);
        setIp(data.localAddress);
        setBroadcastAddress(data.broadcastAddress);
      })
      .catch(err => setError("Không lấy được cấu hình mạng tự động: " + err.message));

    api("/api/state")
      .then(data => {
        setRunning(data.running);
        setLocalAddress(data.localAddress);
        setMessages(data.messages || []);
      })
      .catch(err => setError(err.message));
  }, []);

  useEffect(() => {
    const timer = setInterval(async () => {
      try {
        const data = await api("/api/state");
        setRunning(data.running);
        setLocalAddress(data.localAddress);
        setMessages(data.messages || []);
      } catch (err) {
        setError(err.message);
      }
    }, 600);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const box = chatRef.current;
    if (box) box.scrollTop = box.scrollHeight;
  }, [messages]);

  const start = async () => {
    setError("");
    try {
      const params = new URLSearchParams({
        mode, ip: activeTarget, port, group, groupName, nickname
      });
      const data = await api("/api/start?" + params.toString(), { method: "POST" });
      setRunning(data.running);
    } catch (err) {
      setError(err.message);
    }
  };

  const stop = async () => {
    try {
      await api("/api/stop", { method: "POST" });
      setRunning(false);
    } catch (err) {
      setError(err.message);
    }
  };

  const send = async () => {
    if (!message.trim()) return;
    setError("");
    try {
      const body = new URLSearchParams({
        mode, ip: activeTarget, port, group, groupName, nickname, message
      });
      await api("/api/send", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body
      });
      setMessage("");
    } catch (err) {
      setError(err.message);
    }
  };

  const onMessageKeyDown = event => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-icon">▣</span>
          <span>UDP Chat Application</span>
        </div>
        <div className="top-status">
          <span className={running ? "dot online" : "dot"} />
          {running ? "Đang kết nối UDP" : "Chưa kết nối"}
        </div>
      </header>
      <main className="layout">
        <aside className="sidebar">
          <section className="card personal-card">
            <div className="avatar">●</div>
            <div className="grow">
              <label>Nickname</label>
              <input value={nickname} onChange={e => setNickname(e.target.value)}
                placeholder="Tên hiển thị" maxLength={32} />
            </div>
          </section>
          <section className="card">
            <h3><span>◉</span> Chế độ truyền</h3>
            <div className="mode-grid">
              {modes.map(item => (
                <button key={item.id}
                  className={mode === item.id ? "mode active" : "mode"}
                  onClick={() => setMode(item.id)}>
                  <span className="radio">{item.icon}</span>{item.label}
                </button>
              ))}
            </div>
          </section>
          <section className="card">
            <h3><span>⚙</span> Cấu hình kết nối</h3>
            <Field label={mode === "Broadcast" ? "IP Broadcast (tự động)" : "IP đích"}>
              <input
                value={mode === "Broadcast" ? broadcastAddress : ip}
                onChange={e => mode !== "Broadcast" && setIp(e.target.value)}
                disabled={mode === "Multicast" || mode === "Broadcast"}
              />
            </Field>
            <Field label="Port">
              <input value={port} onChange={e => setPort(e.target.value)}
                inputMode="numeric" />
            </Field>
            <Field label="Multicast Group">
              <input value={group} onChange={e => setGroup(e.target.value)}
                disabled={mode !== "Multicast"} />
            </Field>
            <Field label="Tên nhóm (Group Name)">
              <input value={groupName} onChange={e => setGroupName(e.target.value)}
                maxLength={40} />
            </Field>
          </section>
          <section className="card controls">
            <h3><span>▶</span> Điều khiển</h3>
            <div className="control-row">
              <button className="btn start" onClick={start}>
                ▶&nbsp; {running ? "Đang nhận" : "Bắt đầu nhận"}
              </button>
              <button className="btn stop" onClick={stop}>■&nbsp; Dừng nhận</button>
            </div>
          </section>
          <section className="card status-card">
            <h3><span>●</span> Trạng thái</h3>
            <div className="status-line">
              <span className={running ? "dot online" : "dot"} />
              <span>{running ? "Đang nghe..." : "Đã dừng nhận"}</span>
            </div>
            <div className="address">ⓘ&nbsp; Địa chỉ cục bộ: {localAddress}: {port}</div>
          </section>
        </aside>        <section className="chat-card">
          <div className="chat-header">
            <div className="chat-title"><span className="chat-icon">▣</span><h2>Khung chat</h2></div>
            <div className="group-title"><span>♣</span> Nhóm: <strong>{groupName || "Chưa đặt tên"}</strong></div>
          </div>
          <div className="messages" ref={chatRef}>
            {messages.length === 0 && (
              <div className="empty">Chưa có tin nhắn. Hãy bắt đầu cuộc trò chuyện.</div>
            )}
            {messages.map(item => {
              const own = item.nickname === nickname;
              return (
                <article className={own ? "message own" : "message"}>
                  <div className="message-meta">
                    <strong>{item.nickname || "Người dùng"}</strong>
                    <span>{item.address}</span>
                    <time>{item.time}</time>
                  </div>
                  <div className="message-body">{item.message}</div>
                  {item.groupName && <div className="message-group">#{item.groupName}</div>}
                </article>
              );
            })}
          </div>
          <div className="composer">
            <textarea value={message} onChange={e => setMessage(e.target.value)}
              onKeyDown={onMessageKeyDown} placeholder="Nhập tin nhắn..."
              rows="1" maxLength={2000} />
            <button className="send-btn" onClick={send}>
              <span>➤</span> Gửi
            </button>
          </div>
          {error && <div className="error">⚠ {error}</div>}
          <div className="connection-hint">
            {mode}: <strong>{activeTarget}:{port}</strong>
            {mode === "Multicast" && <> · Group: <strong>{groupName}</strong></>}
          </div>
        </section>
      </main>
    </div>
  );
}

function Field({ label, children }) {
  return <div className="field"><label>{label}</label>{children}</div>;
}

createRoot(document.getElementById("root")).render(<App />);
