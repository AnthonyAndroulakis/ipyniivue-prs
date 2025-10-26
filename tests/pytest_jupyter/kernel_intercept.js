function omitEsmValues(obj) {
	if (obj === null || typeof obj !== "object") {
		return obj;
	}

	if (Array.isArray(obj)) {
		return obj.map((item) => omitEsmValues(item));
	}

	const result = {};

	for (const [key, value] of Object.entries(obj)) {
		if (key === "_esm") {
			result[key] = "esm omitted";
		} else if (value !== null && typeof value === "object") {
			result[key] = omitEsmValues(value);
		} else {
			result[key] = value;
		}
	}

	return result;
}

window.addEventListener("kernel-message", (event) => {
	window.kernel_message_handler(event.detail);
});

window.kernel = {
	modules: {},
	ws: [],
	pending_execs: {},
};
Object.defineProperty(window, "kernel", {
	value: window.kernel,
	writable: false,
	configurable: false,
});

const originalDefineProperty = Object.defineProperty;
Object.defineProperty = new Proxy(originalDefineProperty, {
	apply(target, thisArg, args) {
		if (args[1] === "__esModule" && args[2]?.value) {
			setTimeout(() => {
				const obj = args[0];
				if (obj.serialize) {
					kernel.modules.serializer = obj;
					obj.serialize = new Proxy(obj.serialize, {
						apply: (target, thisArg, args) => {
							const result = target(...args);
							window.dispatchEvent(
								new CustomEvent("kernel-message", {
									detail: {
										direction: "out",
										message: omitEsmValues(args[0]),
										timestamp: new Date().toISOString(),
									},
								}),
							);

							return result;
						},
					});

					obj.deserialize = new Proxy(obj.deserialize, {
						apply: (target, thisArg, args) => {
							const msg = target(...args);
							window.dispatchEvent(
								new CustomEvent("kernel-message", {
									detail: {
										direction: "in",
										message: omitEsmValues(msg),
										timestamp: new Date().toISOString(),
									},
								}),
							);

							const msgId = msg?.parent_header?.msg_id;
							if (msgId && kernel.pending_execs[msgId]) {
								const msgType = msg?.header?.msg_type;
								if (
									msgType === "execute_reply" ||
									msgType === "stream" ||
									msgType === "execute_result" ||
									msgType === "error"
								) {
									const pending = kernel.pending_execs[msgId];

									if (msgType === "stream") {
										pending.output += msg.content.text || "";
									} else if (msgType === "execute_result") {
										pending.output += msg.content.data?.["text/plain"] || "";
									} else if (msgType === "error") {
										pending.error = msg.content;
										pending.resolve({
											error: msg.content,
										});
										delete kernel.pending_execs[msgId];
									} else if (msgType === "execute_reply") {
										if (!pending.error) {
											pending.resolve({
												output: pending.output,
											});
										}
										delete kernel.pending_execs[msgId];
									}
								}
							}

							return msg;
						},
					});
				}
				if (obj.supportedKernelWebSocketProtocols)
					kernel.modules.protocols = obj;
			}, 0);
		}
		return Reflect.apply(target, thisArg, args);
	},
});

window.WebSocket = new Proxy(WebSocket, {
	construct(target, args) {
		const ws = new target(...args);
		if (args[0]?.includes("kernel")) {
			window.kernel.ws.push(ws);
		}
		return ws;
	},
});

window.kernel.send = (msg) => {
	const ws = kernel.ws.find((ws) => ws.readyState === WebSocket.OPEN);
	if (!ws) {
		console.error("No Kernel WebSocket available");
		return;
	}
	const protocol =
		kernel.modules.protocols?.supportedKernelWebSocketProtocols
			?.v1KernelWebsocketJupyterOrg || "";
	ws.send(kernel.modules.serializer.serialize(msg, protocol));
	return msg.header.msg_id;
};

window.kernel.exec = async (code) => {
	const msgId = kernel.send({
		buffers: [],
		channel: "shell",
		content: {
			code: code,
			silent: false,
			store_history: false,
			user_expressions: {},
			allow_stdin: true,
			stop_on_error: false,
		},
		header: {
			msg_id: crypto.randomUUID(),
			session: crypto.randomUUID(),
			username: "",
			date: new Date().toISOString(),
			msg_type: "execute_request",
			version: "5.3",
		},
		metadata: {
			cellId: crypto.randomUUID(),
			deletedCells: [],
			recordTiming: false,
			trusted: true,
		},
		parent_header: {},
	});

	return new Promise((resolve, reject) => {
		kernel.pending_execs[msgId] = {
			resolve,
			reject,
			output: "",
			error: null,
		};

		setTimeout(() => {
			if (kernel.pending_execs[msgId]) {
				delete kernel.pending_execs[msgId];
				reject(new Error("Execution timeout"));
			}
		}, 10000);
	});
};
window.get_nv_ref = async (name) => {
	const result = await window.kernel.exec(`${name}.model_id`);
	if (result.error || !result.output) {
		return {
			error: `Could not get model ID for backend variable ${name}.`,
		};
	}
	const modelId = result.output.trim().replace(/['"]/g, "");
	if (!modelId) {
		return {
			error: `Empty model ID for backend variable ${name}.`,
		};
	}
	const nvInst = window.nvTestInstances?.[modelId];
	if (!nvInst) {
		return {
			error: `Could not find frontend NV instance. ModelID: ${modelId}`,
		};
	}
	return nvInst;
};
