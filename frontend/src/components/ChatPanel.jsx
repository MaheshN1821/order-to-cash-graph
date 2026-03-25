import { useState, useRef, useEffect } from "react";
import {
	Send,
	Loader,
	ShieldAlert,
	ChevronDown,
	ChevronUp,
	Database,
} from "lucide-react";
import { sendQuery } from "../lib/api";

const SUGGESTIONS = [
	"Which products have the most billing documents?",
	"Show me all cancelled billing documents",
	"Which sales orders are delivered but not billed?",
	"Trace the flow of billing document 90504248",
];

export default function ChatPanel({ onQueryResults }) {
	const [messages, setMessages] = useState([]);
	const [input, setInput] = useState("");
	const [loading, setLoading] = useState(false);
	const bottomRef = useRef(null);

	useEffect(() => {
		bottomRef.current?.scrollIntoView({ behavior: "smooth" });
	}, [messages, loading]);

	async function submit(msg) {
		const text = (msg || input).trim();
		if (!text || loading) return;
		setInput("");
		setMessages((prev) => [...prev, { role: "user", text }]);
		setLoading(true);
		try {
			const res = await sendQuery(text);
			console.log(res);

			setMessages((prev) => [
				...prev,
				{
					role: "ai",
					text: res.answer,
					sql: res.sql,
					results: res.results,
					rejected: res.rejected,
				},
			]);
			if (!res.rejected && res.results?.length) onQueryResults?.(res.results);
		} catch {
			setMessages((prev) => [
				...prev,
				{
					role: "ai",
					text: "Connection error — is the backend running?",
					rejected: false,
				},
			]);
		} finally {
			setLoading(false);
		}
	}

	function SqlToggle({ sql, resultCount }) {
		const [open, setOpen] = useState(false);
		if (!sql) return null;
		return (
			<div style={{ marginTop: 6 }}>
				<button
					onClick={() => setOpen((o) => !o)}
					style={{
						display: "flex",
						alignItems: "center",
						gap: 4,
						fontSize: 11,
						color: "#4e4e50",
						// color: "#717277",
						fontFamily: "IBM Plex Mono, monospace",
						background: "none",
						border: "none",
						cursor: "pointer",
						padding: 0,
					}}
				>
					<Database size={10} />
					{open ? "hide sql" : "show sql"}
					{open ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
					{resultCount !== undefined && (
						<span style={{ marginLeft: 4 }}>
							· {resultCount} row{resultCount !== 1 ? "s" : ""}
						</span>
					)}
				</button>
				{open && (
					<pre
						style={{
							marginTop: 6,
							background: "#f5f6fa",
							border: "1px solid #e2e4eb",
							borderRadius: 6,
							padding: "8px 10px",
							fontFamily: "IBM Plex Mono, monospace",
							fontSize: 11,
							color: "#4f46e5",
							whiteSpace: "pre-wrap",
							wordBreak: "break-all",
							lineHeight: 1.6,
							maxHeight: 160,
							overflowY: "auto",
						}}
					>
						{sql}
					</pre>
				)}
			</div>
		);
	}

	return (
		<div
			style={{
				display: "flex",
				flexDirection: "column",
				height: "100%",
				background: "#ffffff",
				borderLeft: "1px solid #e2e4eb",
			}}
		>
			{/* Header */}
			<div
				style={{
					padding: "12px 16px",
					borderBottom: "1px solid #e2e4eb",
					display: "flex",
					alignItems: "center",
					gap: 8,
				}}
			>
				<div
					style={{
						width: 8,
						height: 8,
						borderRadius: "50%",
						background: "#16a34a",
						boxShadow: "0 0 5px #16a34a",
					}}
				/>
				<span style={{ fontWeight: 600, fontSize: 13, color: "#1a1d2e" }}>
					Chat with Graph
				</span>
				<span
					style={{
						marginLeft: "auto",
						fontSize: 11,
						color: "#9296aa",
						fontFamily: "IBM Plex Mono, monospace",
					}}
				>
					Order to Cash
				</span>
			</div>

			{/* Messages */}
			<div
				style={{
					flex: 1,
					overflowY: "auto",
					padding: "14px",
					display: "flex",
					flexDirection: "column",
					gap: 12,
				}}
			>
				{messages.length === 0 && (
					<div style={{ textAlign: "center", padding: "20px 8px" }}>
						<div
							style={{
								width: 40,
								height: 40,
								borderRadius: 10,
								background: "#4f46e5",
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								fontSize: 16,
								fontWeight: 700,
								color: "#fff",
								margin: "0 auto 12px",
							}}
						>
							G
						</div>
						<div
							style={{
								fontWeight: 600,
								fontSize: 14,
								color: "#1a1d2e",
								marginBottom: 4,
							}}
						>
							Graph Agent
						</div>
						<div
							style={{
								fontSize: 12,
								color: "#9296aa",
								marginBottom: 16,
								lineHeight: 1.6,
							}}
						>
							Ask anything about your Order to Cash data.
						</div>
						<div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
							{SUGGESTIONS.map((s) => (
								<button
									key={s}
									onClick={() => submit(s)}
									style={{
										background: "#f5f6fa",
										border: "1px solid #e2e4eb",
										borderRadius: 8,
										padding: "8px 12px",
										color: "#52566b",
										fontSize: 12,
										textAlign: "left",
										cursor: "pointer",
										fontFamily: "Syne, sans-serif",
										lineHeight: 1.4,
										transition: "border-color 0.15s",
									}}
									onMouseEnter={(e) => (e.target.style.borderColor = "#4f46e5")}
									onMouseLeave={(e) => (e.target.style.borderColor = "#e2e4eb")}
								>
									{s}
								</button>
							))}
						</div>
					</div>
				)}

				{messages.map((msg, i) => (
					<div key={i}>
						{msg.role === "user" ? (
							<div style={{ display: "flex", justifyContent: "flex-end" }}>
								<div
									style={{
										background: "#4f46e5",
										color: "#fff",
										padding: "8px 12px",
										borderRadius: "12px 12px 3px 12px",
										maxWidth: "85%",
										fontSize: 13,
										lineHeight: 1.5,
									}}
								>
									{msg.text}
								</div>
							</div>
						) : (
							<div
								style={{ display: "flex", alignItems: "flex-start", gap: 8 }}
							>
								<div
									style={{
										width: 26,
										height: 26,
										borderRadius: 7,
										background: "#4f46e5",
										flexShrink: 0,
										display: "flex",
										alignItems: "center",
										justifyContent: "center",
										fontSize: 11,
										fontWeight: 700,
										color: "#fff",
									}}
								>
									G
								</div>
								<div style={{ flex: 1, minWidth: 0 }}>
									{msg.rejected ? (
										<div
											style={{
												background: "#fffbeb",
												border: "1px solid #fde68a",
												borderRadius: "3px 12px 12px 12px",
												padding: "9px 12px",
												fontSize: 13,
												lineHeight: 1.6,
												color: "#92400e",
												display: "flex",
												gap: 8,
											}}
										>
											<ShieldAlert
												size={14}
												style={{ flexShrink: 0, marginTop: 2 }}
											/>
											{msg.text}
										</div>
									) : (
										<div
											style={{
												background: "#f5f6fa",
												border: "1px solid #e2e4eb",
												borderRadius: "3px 12px 12px 12px",
												padding: "9px 12px",
												fontSize: 13,
												lineHeight: 1.6,
												color: "#1a1d2e",
											}}
										>
											{msg.text}
										</div>
									)}
									{!msg.rejected && (
										<SqlToggle
											sql={msg.sql}
											resultCount={msg.results?.length}
										/>
									)}
								</div>
							</div>
						)}
					</div>
				))}

				{loading && (
					<div style={{ display: "flex", alignItems: "center", gap: 8 }}>
						<div
							style={{
								width: 26,
								height: 26,
								borderRadius: 7,
								background: "#4f46e5",
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								fontSize: 11,
								fontWeight: 700,
								color: "#fff",
							}}
						>
							G
						</div>
						<div
							style={{
								background: "#f5f6fa",
								border: "1px solid #e2e4eb",
								borderRadius: "3px 12px 12px 12px",
								padding: "10px 14px",
								display: "flex",
								gap: 4,
								alignItems: "center",
							}}
						>
							<style>{`@keyframes dot{0%,100%{opacity:.3}50%{opacity:1}}`}</style>
							{[0, 0.2, 0.4].map((d, i) => (
								<span
									key={i}
									style={{
										width: 6,
										height: 6,
										borderRadius: "50%",
										background: "#9296aa",
										display: "inline-block",
										animation: `dot 1.2s ease-in-out ${d}s infinite`,
									}}
								/>
							))}
						</div>
					</div>
				)}
				<div ref={bottomRef} />
			</div>

			{/* Input */}
			<div
				style={{
					padding: "10px 14px",
					borderTop: "1px solid #e2e4eb",
					display: "flex",
					gap: 8,
					alignItems: "flex-end",
					background: "#fff",
				}}
			>
				<textarea
					style={{
						flex: 1,
						background: "#f5f6fa",
						border: "1px solid #e2e4eb",
						borderRadius: 8,
						padding: "8px 11px",
						color: "#1a1d2e",
						fontFamily: "Syne, sans-serif",
						fontSize: 13,
						resize: "none",
						outline: "none",
						lineHeight: 1.5,
						minHeight: 38,
						maxHeight: 100,
						transition: "border-color 0.15s",
					}}
					placeholder="Ask about your O2C data…"
					value={input}
					onChange={(e) => setInput(e.target.value)}
					onKeyDown={(e) => {
						if (e.key === "Enter" && !e.shiftKey) {
							e.preventDefault();
							submit();
						}
					}}
					onFocus={(e) => (e.target.style.borderColor = "#4f46e5")}
					onBlur={(e) => (e.target.style.borderColor = "#e2e4eb")}
					rows={1}
				/>
				<button
					onClick={() => submit()}
					disabled={loading || !input.trim()}
					style={{
						width: 38,
						height: 38,
						borderRadius: 8,
						background: "#4f46e5",
						border: "none",
						cursor: "pointer",
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						color: "#fff",
						flexShrink: 0,
						opacity: loading || !input.trim() ? 0.5 : 1,
						transition: "opacity 0.15s",
					}}
				>
					{loading ? (
						<Loader
							size={15}
							style={{ animation: "spin 1s linear infinite" }}
						/>
					) : (
						<Send size={15} />
					)}
				</button>
				<style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
			</div>
		</div>
	);
}
