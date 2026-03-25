import { X, GitBranch, ArrowDownRight } from "lucide-react";
import {
	TYPE_COLOR,
	TYPE_LABEL,
	formatMetaValue,
	HIDDEN_META_KEYS,
} from "../lib/graphUtils";

export default function NodePanel({ node, onClose, onExpand, onTraceFlow }) {
	if (!node) return null;

	const meta = node.meta || node;
	const type = meta.entity_type || node.entity_type;
	const label = meta.label || node.label;
	const color = TYPE_COLOR[type] || "#94a3b8";

	// Build display fields — skip internal keys
	const displayEntries = Object.entries(meta).filter(
		([k]) => !HIDDEN_META_KEYS.has(k) && k !== "meta",
	);

	return (
		<>
			<style>{`
        @keyframes slideIn {
          from { transform: translateX(24px); opacity: 0; }
          to   { transform: translateX(0);   opacity: 1; }
        }
      `}</style>
			<div
				style={{
					position: "absolute",
					top: 16,
					left: 16,
					width: 300,
					maxHeight: "calc(100% - 32px)",
					background: "#ffffff",
					border: "1px solid #e2e4eb",
					borderRadius: 12,
					boxShadow: "0 8px 32px rgba(0,0,0,0.12)",
					display: "flex",
					flexDirection: "column",
					zIndex: 20,
					animation: "slideIn 0.18s ease",
					overflow: "hidden",
				}}
			>
				{/* Coloured top stripe */}
				<div
					style={{
						height: 4,
						background: color,
						borderRadius: "12px 12px 0 0",
					}}
				/>

				{/* Header */}
				<div
					style={{
						padding: "12px 14px 10px",
						borderBottom: "1px solid #f0f1f5",
						display: "flex",
						alignItems: "flex-start",
						gap: 10,
					}}
				>
					<div style={{ flex: 1, minWidth: 0 }}>
						{/* Type badge */}
						<div
							style={{
								display: "inline-flex",
								alignItems: "center",
								gap: 5,
								padding: "2px 8px",
								borderRadius: 20,
								fontSize: 10,
								fontFamily: "IBM Plex Mono, monospace",
								fontWeight: 500,
								letterSpacing: "0.04em",
								background: color + "18",
								color: color,
								marginBottom: 5,
							}}
						>
							<span
								style={{
									width: 5,
									height: 5,
									borderRadius: "50%",
									background: color,
								}}
							/>
							{TYPE_LABEL[type] || type}
						</div>
						{/* Label */}
						<div
							style={{
								fontWeight: 600,
								fontSize: 14,
								color: "#1a1d2e",
								lineHeight: 1.3,
								wordBreak: "break-word",
							}}
						>
							{label}
						</div>
					</div>
					<button
						onClick={onClose}
						style={{
							background: "#f0f1f5",
							border: "none",
							borderRadius: 6,
							width: 26,
							height: 26,
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							cursor: "pointer",
							color: "#52566b",
							flexShrink: 0,
						}}
					>
						<X size={13} />
					</button>
				</div>

				{/* Connections count */}
				<div
					style={{
						padding: "7px 14px",
						borderBottom: "1px solid #f0f1f5",
						display: "flex",
						gap: 16,
						fontSize: 11,
						fontFamily: "IBM Plex Mono, monospace",
						color: "#9296aa",
					}}
				>
					<span>
						<b style={{ color: "#1a1d2e" }}>{meta.in_degree ?? "?"}</b> in
					</span>
					<span>
						<b style={{ color: "#1a1d2e" }}>{meta.out_degree ?? "?"}</b> out
					</span>
					<span>
						<b style={{ color: "#1a1d2e" }}>
							{(meta.in_degree ?? 0) + (meta.out_degree ?? 0)}
						</b>{" "}
						connections
					</span>
				</div>

				{/* Metadata rows */}
				<div style={{ flex: 1, overflowY: "auto", padding: "8px 14px 12px" }}>
					<div
						style={{
							fontSize: 10,
							letterSpacing: "0.08em",
							color: "#9296aa",
							fontFamily: "IBM Plex Mono, monospace",
							textTransform: "uppercase",
							marginBottom: 8,
							marginTop: 4,
						}}
					>
						Properties
					</div>

					{displayEntries.map(([k, v]) => (
						<div
							key={k}
							style={{
								display: "flex",
								justifyContent: "space-between",
								alignItems: "flex-start",
								padding: "4px 0",
								borderBottom: "1px solid #f5f6fa",
								gap: 8,
							}}
						>
							<span
								style={{
									fontSize: 11,
									color: "#9296aa",
									fontFamily: "IBM Plex Mono, monospace",
									flexShrink: 0,
									minWidth: 90,
									paddingTop: 1,
								}}
							>
								{k.replace(/_/g, " ")}
							</span>
							<span
								style={{
									fontSize: 11,
									color: "#1a1d2e",
									fontFamily: "IBM Plex Mono, monospace",
									textAlign: "right",
									wordBreak: "break-all",
								}}
							>
								{formatMetaValue(k, v)}
							</span>
						</div>
					))}

					{displayEntries.length === 0 && (
						<div
							style={{ fontSize: 12, color: "#9296aa", fontStyle: "italic" }}
						>
							No additional properties
						</div>
					)}
				</div>

				{/* Action buttons */}
				<div
					style={{
						padding: "10px 14px",
						borderTop: "1px solid #f0f1f5",
						display: "flex",
						gap: 8,
					}}
				>
					<button
						onClick={() => onExpand(node.id)}
						style={{
							flex: 1,
							padding: "7px 10px",
							borderRadius: 8,
							border: "none",
							background: color,
							color: "#fff",
							fontFamily: "Syne, sans-serif",
							fontWeight: 500,
							fontSize: 12,
							cursor: "pointer",
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							gap: 5,
						}}
					>
						<GitBranch size={12} />
						Expand
					</button>
					<button
						onClick={() => onTraceFlow(node.id)}
						style={{
							flex: 1,
							padding: "7px 10px",
							borderRadius: 8,
							border: "1px solid #e2e4eb",
							background: "#ffffff",
							color: "#52566b",
							fontFamily: "Syne, sans-serif",
							fontWeight: 500,
							fontSize: 12,
							cursor: "pointer",
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							gap: 5,
						}}
					>
						<ArrowDownRight size={12} />
						Trace flow
					</button>
				</div>
			</div>
		</>
	);
}
