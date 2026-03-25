import React from "react";
import { TYPE_COLOR, TYPE_LABEL } from "../lib/graphUtils";

const ENTITY_ORDER = [
	"customer",
	"sales_order",
	"delivery",
	"billing_doc",
	"journal_entry",
	"payment",
	"product",
	"plant",
];

export default function Toolbar({ stats, onReset, filterType, onFilterType }) {
	return (
		<div
			style={{
				position: "absolute",
				top: 0,
				left: 0,
				right: 0,
				height: 48,
				background: "rgba(255,255,255,0.97)",
				borderBottom: "1px solid #e5e7eb",
				display: "flex",
				alignItems: "center",
				padding: "0 16px",
				gap: 10,
				zIndex: 10,
				backdropFilter: "blur(8px)",
			}}
		>
			{/* Stats pills */}
			{stats && (
				<div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
					{[
						{ label: "nodes", val: stats.total_nodes },
						{ label: "edges", val: stats.total_edges },
					].map(({ label, val }) => (
						<div
							key={label}
							style={{
								padding: "2px 10px",
								borderRadius: 20,
								background: "#f3f4f6",
								border: "1px solid #e5e7eb",
								fontSize: 11,
								fontFamily: "IBM Plex Mono, monospace",
								color: "#6b7280",
								whiteSpace: "nowrap",
							}}
						>
							<span style={{ color: "#111827", fontWeight: 600 }}>{val}</span>{" "}
							{label}
						</div>
					))}
				</div>
			)}

			{/* Divider */}
			<div
				style={{ width: 1, height: 22, background: "#e5e7eb", flexShrink: 0 }}
			/>

			{/* Clickable legend tags — click to filter, click again to clear */}
			<div
				style={{
					display: "flex",
					gap: 6,
					flex: 1,
					overflowX: "auto",
					alignItems: "center",
				}}
			>
				{ENTITY_ORDER.map((type) => {
					const active = filterType === type;
					const color = TYPE_COLOR[type];
					return (
						<button
							key={type}
							onClick={() => onFilterType(active ? null : type)}
							title={
								active
									? `Clear ${TYPE_LABEL[type]} filter`
									: `Show only ${TYPE_LABEL[type]}`
							}
							style={{
								display: "flex",
								alignItems: "center",
								gap: 5,
								padding: "3px 10px 3px 7px",
								borderRadius: 20,
								border: `1.5px solid ${active ? color : "#e5e7eb"}`,
								background: active ? color + "18" : "#ffffff",
								cursor: "pointer",
								fontSize: 11,
								fontFamily: "Syne, sans-serif",
								fontWeight: active ? 600 : 400,
								color: active ? color : "#6b7280",
								whiteSpace: "nowrap",
								flexShrink: 0,
								transition: "all 0.15s",
								outline: "none",
							}}
							onMouseEnter={(e) => {
								if (!active) e.currentTarget.style.borderColor = color;
							}}
							onMouseLeave={(e) => {
								if (!active) e.currentTarget.style.borderColor = "#e5e7eb";
							}}
						>
							{/* Coloured dot */}
							<span
								style={{
									width: 8,
									height: 8,
									borderRadius: "50%",
									background: "transparent",
									border: `2px solid ${color}`,
									flexShrink: 0,
									...(active ? { background: color } : {}),
								}}
							/>
							{TYPE_LABEL[type]}
							{stats?.nodes_by_type?.[type] !== undefined && (
								<span
									style={{
										fontFamily: "IBM Plex Mono, monospace",
										fontSize: 10,
										color: active ? color : "#9ca3af",
									}}
								>
									{stats.nodes_by_type[type]}
								</span>
							)}
						</button>
					);
				})}
			</div>

			{/* Reset */}
			<button
				onClick={onReset}
				style={{
					padding: "5px 12px",
					borderRadius: 8,
					border: "1px solid #e5e7eb",
					background: "#fff",
					color: "#6b7280",
					fontFamily: "Syne, sans-serif",
					fontSize: 11,
					fontWeight: 500,
					cursor: "pointer",
					whiteSpace: "nowrap",
					flexShrink: 0,
					transition: "border-color 0.15s",
				}}
				onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#6b7280")}
				onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#e5e7eb")}
			>
				Reset view
			</button>
		</div>
	);
}

