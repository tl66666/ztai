//#region \0rolldown/runtime.js
var e = Object.defineProperty, t = (e, t) => () => (t || (e((t = { exports: {} }).exports, t), e = null), t.exports), n = (t, n) => {
	let r = {};
	for (var i in t) e(r, i, {
		get: t[i],
		enumerable: !0
	});
	return n || e(r, Symbol.toStringTag, { value: "Module" }), r;
}, r = /* @__PURE__ */ t(((e) => {
	var t = Symbol.for("react.transitional.element"), n = Symbol.for("react.portal"), r = Symbol.for("react.fragment"), i = Symbol.for("react.strict_mode"), a = Symbol.for("react.profiler"), o = Symbol.for("react.consumer"), s = Symbol.for("react.context"), c = Symbol.for("react.forward_ref"), l = Symbol.for("react.suspense"), u = Symbol.for("react.memo"), d = Symbol.for("react.lazy"), f = Symbol.for("react.activity"), p = Symbol.iterator;
	function m(e) {
		return typeof e != "object" || !e ? null : (e = p && e[p] || e["@@iterator"], typeof e == "function" ? e : null);
	}
	var h = {
		isMounted: function() {
			return !1;
		},
		enqueueForceUpdate: function() {},
		enqueueReplaceState: function() {},
		enqueueSetState: function() {}
	}, g = Object.assign, _ = {};
	function v(e, t, n) {
		this.props = e, this.context = t, this.refs = _, this.updater = n || h;
	}
	v.prototype.isReactComponent = {}, v.prototype.setState = function(e, t) {
		if (typeof e != "object" && typeof e != "function" && e != null) throw Error("takes an object of state variables to update or a function which returns an object of state variables.");
		this.updater.enqueueSetState(this, e, t, "setState");
	}, v.prototype.forceUpdate = function(e) {
		this.updater.enqueueForceUpdate(this, e, "forceUpdate");
	};
	function y() {}
	y.prototype = v.prototype;
	function b(e, t, n) {
		this.props = e, this.context = t, this.refs = _, this.updater = n || h;
	}
	var x = b.prototype = new y();
	x.constructor = b, g(x, v.prototype), x.isPureReactComponent = !0;
	var S = Array.isArray;
	function C() {}
	var w = {
		H: null,
		A: null,
		T: null,
		S: null
	}, T = Object.prototype.hasOwnProperty;
	function ee(e, n, r) {
		var i = r.ref;
		return {
			$$typeof: t,
			type: e,
			key: n,
			ref: i === void 0 ? null : i,
			props: r
		};
	}
	function te(e, t) {
		return ee(e.type, t, e.props);
	}
	function E(e) {
		return typeof e == "object" && !!e && e.$$typeof === t;
	}
	function ne(e) {
		var t = {
			"=": "=0",
			":": "=2"
		};
		return "$" + e.replace(/[=:]/g, function(e) {
			return t[e];
		});
	}
	var re = /\/+/g;
	function ie(e, t) {
		return typeof e == "object" && e && e.key != null ? ne("" + e.key) : t.toString(36);
	}
	function ae(e) {
		switch (e.status) {
			case "fulfilled": return e.value;
			case "rejected": throw e.reason;
			default: switch (typeof e.status == "string" ? e.then(C, C) : (e.status = "pending", e.then(function(t) {
				e.status === "pending" && (e.status = "fulfilled", e.value = t);
			}, function(t) {
				e.status === "pending" && (e.status = "rejected", e.reason = t);
			})), e.status) {
				case "fulfilled": return e.value;
				case "rejected": throw e.reason;
			}
		}
		throw e;
	}
	function D(e, r, i, a, o) {
		var s = typeof e;
		(s === "undefined" || s === "boolean") && (e = null);
		var c = !1;
		if (e === null) c = !0;
		else switch (s) {
			case "bigint":
			case "string":
			case "number":
				c = !0;
				break;
			case "object": switch (e.$$typeof) {
				case t:
				case n:
					c = !0;
					break;
				case d: return c = e._init, D(c(e._payload), r, i, a, o);
			}
		}
		if (c) return o = o(e), c = a === "" ? "." + ie(e, 0) : a, S(o) ? (i = "", c != null && (i = c.replace(re, "$&/") + "/"), D(o, r, i, "", function(e) {
			return e;
		})) : o != null && (E(o) && (o = te(o, i + (o.key == null || e && e.key === o.key ? "" : ("" + o.key).replace(re, "$&/") + "/") + c)), r.push(o)), 1;
		c = 0;
		var l = a === "" ? "." : a + ":";
		if (S(e)) for (var u = 0; u < e.length; u++) a = e[u], s = l + ie(a, u), c += D(a, r, i, s, o);
		else if (u = m(e), typeof u == "function") for (e = u.call(e), u = 0; !(a = e.next()).done;) a = a.value, s = l + ie(a, u++), c += D(a, r, i, s, o);
		else if (s === "object") {
			if (typeof e.then == "function") return D(ae(e), r, i, a, o);
			throw r = String(e), Error("Objects are not valid as a React child (found: " + (r === "[object Object]" ? "object with keys {" + Object.keys(e).join(", ") + "}" : r) + "). If you meant to render a collection of children, use an array instead.");
		}
		return c;
	}
	function oe(e, t, n) {
		if (e == null) return e;
		var r = [], i = 0;
		return D(e, r, "", "", function(e) {
			return t.call(n, e, i++);
		}), r;
	}
	function se(e) {
		if (e._status === -1) {
			var t = e._result;
			t = t(), t.then(function(t) {
				(e._status === 0 || e._status === -1) && (e._status = 1, e._result = t);
			}, function(t) {
				(e._status === 0 || e._status === -1) && (e._status = 2, e._result = t);
			}), e._status === -1 && (e._status = 0, e._result = t);
		}
		if (e._status === 1) return e._result.default;
		throw e._result;
	}
	var O = typeof reportError == "function" ? reportError : function(e) {
		if (typeof window == "object" && typeof window.ErrorEvent == "function") {
			var t = new window.ErrorEvent("error", {
				bubbles: !0,
				cancelable: !0,
				message: typeof e == "object" && e && typeof e.message == "string" ? String(e.message) : String(e),
				error: e
			});
			if (!window.dispatchEvent(t)) return;
		} else if (typeof process == "object" && typeof process.emit == "function") {
			process.emit("uncaughtException", e);
			return;
		}
		console.error(e);
	}, k = {
		map: oe,
		forEach: function(e, t, n) {
			oe(e, function() {
				t.apply(this, arguments);
			}, n);
		},
		count: function(e) {
			var t = 0;
			return oe(e, function() {
				t++;
			}), t;
		},
		toArray: function(e) {
			return oe(e, function(e) {
				return e;
			}) || [];
		},
		only: function(e) {
			if (!E(e)) throw Error("React.Children.only expected to receive a single React element child.");
			return e;
		}
	};
	e.Activity = f, e.Children = k, e.Component = v, e.Fragment = r, e.Profiler = a, e.PureComponent = b, e.StrictMode = i, e.Suspense = l, e.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE = w, e.__COMPILER_RUNTIME = {
		__proto__: null,
		c: function(e) {
			return w.H.useMemoCache(e);
		}
	}, e.cache = function(e) {
		return function() {
			return e.apply(null, arguments);
		};
	}, e.cacheSignal = function() {
		return null;
	}, e.cloneElement = function(e, t, n) {
		if (e == null) throw Error("The argument must be a React element, but you passed " + e + ".");
		var r = g({}, e.props), i = e.key;
		if (t != null) for (a in t.key !== void 0 && (i = "" + t.key), t) !T.call(t, a) || a === "key" || a === "__self" || a === "__source" || a === "ref" && t.ref === void 0 || (r[a] = t[a]);
		var a = arguments.length - 2;
		if (a === 1) r.children = n;
		else if (1 < a) {
			for (var o = Array(a), s = 0; s < a; s++) o[s] = arguments[s + 2];
			r.children = o;
		}
		return ee(e.type, i, r);
	}, e.createContext = function(e) {
		return e = {
			$$typeof: s,
			_currentValue: e,
			_currentValue2: e,
			_threadCount: 0,
			Provider: null,
			Consumer: null
		}, e.Provider = e, e.Consumer = {
			$$typeof: o,
			_context: e
		}, e;
	}, e.createElement = function(e, t, n) {
		var r, i = {}, a = null;
		if (t != null) for (r in t.key !== void 0 && (a = "" + t.key), t) T.call(t, r) && r !== "key" && r !== "__self" && r !== "__source" && (i[r] = t[r]);
		var o = arguments.length - 2;
		if (o === 1) i.children = n;
		else if (1 < o) {
			for (var s = Array(o), c = 0; c < o; c++) s[c] = arguments[c + 2];
			i.children = s;
		}
		if (e && e.defaultProps) for (r in o = e.defaultProps, o) i[r] === void 0 && (i[r] = o[r]);
		return ee(e, a, i);
	}, e.createRef = function() {
		return { current: null };
	}, e.forwardRef = function(e) {
		return {
			$$typeof: c,
			render: e
		};
	}, e.isValidElement = E, e.lazy = function(e) {
		return {
			$$typeof: d,
			_payload: {
				_status: -1,
				_result: e
			},
			_init: se
		};
	}, e.memo = function(e, t) {
		return {
			$$typeof: u,
			type: e,
			compare: t === void 0 ? null : t
		};
	}, e.startTransition = function(e) {
		var t = w.T, n = {};
		w.T = n;
		try {
			var r = e(), i = w.S;
			i !== null && i(n, r), typeof r == "object" && r && typeof r.then == "function" && r.then(C, O);
		} catch (e) {
			O(e);
		} finally {
			t !== null && n.types !== null && (t.types = n.types), w.T = t;
		}
	}, e.unstable_useCacheRefresh = function() {
		return w.H.useCacheRefresh();
	}, e.use = function(e) {
		return w.H.use(e);
	}, e.useActionState = function(e, t, n) {
		return w.H.useActionState(e, t, n);
	}, e.useCallback = function(e, t) {
		return w.H.useCallback(e, t);
	}, e.useContext = function(e) {
		return w.H.useContext(e);
	}, e.useDebugValue = function() {}, e.useDeferredValue = function(e, t) {
		return w.H.useDeferredValue(e, t);
	}, e.useEffect = function(e, t) {
		return w.H.useEffect(e, t);
	}, e.useEffectEvent = function(e) {
		return w.H.useEffectEvent(e);
	}, e.useId = function() {
		return w.H.useId();
	}, e.useImperativeHandle = function(e, t, n) {
		return w.H.useImperativeHandle(e, t, n);
	}, e.useInsertionEffect = function(e, t) {
		return w.H.useInsertionEffect(e, t);
	}, e.useLayoutEffect = function(e, t) {
		return w.H.useLayoutEffect(e, t);
	}, e.useMemo = function(e, t) {
		return w.H.useMemo(e, t);
	}, e.useOptimistic = function(e, t) {
		return w.H.useOptimistic(e, t);
	}, e.useReducer = function(e, t, n) {
		return w.H.useReducer(e, t, n);
	}, e.useRef = function(e) {
		return w.H.useRef(e);
	}, e.useState = function(e) {
		return w.H.useState(e);
	}, e.useSyncExternalStore = function(e, t, n) {
		return w.H.useSyncExternalStore(e, t, n);
	}, e.useTransition = function() {
		return w.H.useTransition();
	}, e.version = "19.2.8";
})), i = /* @__PURE__ */ t(((e, t) => {
	t.exports = r();
})), a = /* @__PURE__ */ t(((e) => {
	function t(e, t) {
		var n = e.length;
		e.push(t);
		a: for (; 0 < n;) {
			var r = n - 1 >>> 1, a = e[r];
			if (0 < i(a, t)) e[r] = t, e[n] = a, n = r;
			else break a;
		}
	}
	function n(e) {
		return e.length === 0 ? null : e[0];
	}
	function r(e) {
		if (e.length === 0) return null;
		var t = e[0], n = e.pop();
		if (n !== t) {
			e[0] = n;
			a: for (var r = 0, a = e.length, o = a >>> 1; r < o;) {
				var s = 2 * (r + 1) - 1, c = e[s], l = s + 1, u = e[l];
				if (0 > i(c, n)) l < a && 0 > i(u, c) ? (e[r] = u, e[l] = n, r = l) : (e[r] = c, e[s] = n, r = s);
				else if (l < a && 0 > i(u, n)) e[r] = u, e[l] = n, r = l;
				else break a;
			}
		}
		return t;
	}
	function i(e, t) {
		var n = e.sortIndex - t.sortIndex;
		return n === 0 ? e.id - t.id : n;
	}
	if (e.unstable_now = void 0, typeof performance == "object" && typeof performance.now == "function") {
		var a = performance;
		e.unstable_now = function() {
			return a.now();
		};
	} else {
		var o = Date, s = o.now();
		e.unstable_now = function() {
			return o.now() - s;
		};
	}
	var c = [], l = [], u = 1, d = null, f = 3, p = !1, m = !1, h = !1, g = !1, _ = typeof setTimeout == "function" ? setTimeout : null, v = typeof clearTimeout == "function" ? clearTimeout : null, y = typeof setImmediate < "u" ? setImmediate : null;
	function b(e) {
		for (var i = n(l); i !== null;) {
			if (i.callback === null) r(l);
			else if (i.startTime <= e) r(l), i.sortIndex = i.expirationTime, t(c, i);
			else break;
			i = n(l);
		}
	}
	function x(e) {
		if (h = !1, b(e), !m) if (n(c) !== null) m = !0, S || (S = !0, E());
		else {
			var t = n(l);
			t !== null && ie(x, t.startTime - e);
		}
	}
	var S = !1, C = -1, w = 5, T = -1;
	function ee() {
		return g ? !0 : !(e.unstable_now() - T < w);
	}
	function te() {
		if (g = !1, S) {
			var t = e.unstable_now();
			T = t;
			var i = !0;
			try {
				a: {
					m = !1, h && (h = !1, v(C), C = -1), p = !0;
					var a = f;
					try {
						b: {
							for (b(t), d = n(c); d !== null && !(d.expirationTime > t && ee());) {
								var o = d.callback;
								if (typeof o == "function") {
									d.callback = null, f = d.priorityLevel;
									var s = o(d.expirationTime <= t);
									if (t = e.unstable_now(), typeof s == "function") {
										d.callback = s, b(t), i = !0;
										break b;
									}
									d === n(c) && r(c), b(t);
								} else r(c);
								d = n(c);
							}
							if (d !== null) i = !0;
							else {
								var u = n(l);
								u !== null && ie(x, u.startTime - t), i = !1;
							}
						}
						break a;
					} finally {
						d = null, f = a, p = !1;
					}
					i = void 0;
				}
			} finally {
				i ? E() : S = !1;
			}
		}
	}
	var E;
	if (typeof y == "function") E = function() {
		y(te);
	};
	else if (typeof MessageChannel < "u") {
		var ne = new MessageChannel(), re = ne.port2;
		ne.port1.onmessage = te, E = function() {
			re.postMessage(null);
		};
	} else E = function() {
		_(te, 0);
	};
	function ie(t, n) {
		C = _(function() {
			t(e.unstable_now());
		}, n);
	}
	e.unstable_IdlePriority = 5, e.unstable_ImmediatePriority = 1, e.unstable_LowPriority = 4, e.unstable_NormalPriority = 3, e.unstable_Profiling = null, e.unstable_UserBlockingPriority = 2, e.unstable_cancelCallback = function(e) {
		e.callback = null;
	}, e.unstable_forceFrameRate = function(e) {
		0 > e || 125 < e ? console.error("forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported") : w = 0 < e ? Math.floor(1e3 / e) : 5;
	}, e.unstable_getCurrentPriorityLevel = function() {
		return f;
	}, e.unstable_next = function(e) {
		switch (f) {
			case 1:
			case 2:
			case 3:
				var t = 3;
				break;
			default: t = f;
		}
		var n = f;
		f = t;
		try {
			return e();
		} finally {
			f = n;
		}
	}, e.unstable_requestPaint = function() {
		g = !0;
	}, e.unstable_runWithPriority = function(e, t) {
		switch (e) {
			case 1:
			case 2:
			case 3:
			case 4:
			case 5: break;
			default: e = 3;
		}
		var n = f;
		f = e;
		try {
			return t();
		} finally {
			f = n;
		}
	}, e.unstable_scheduleCallback = function(r, i, a) {
		var o = e.unstable_now();
		switch (typeof a == "object" && a ? (a = a.delay, a = typeof a == "number" && 0 < a ? o + a : o) : a = o, r) {
			case 1:
				var s = -1;
				break;
			case 2:
				s = 250;
				break;
			case 5:
				s = 1073741823;
				break;
			case 4:
				s = 1e4;
				break;
			default: s = 5e3;
		}
		return s = a + s, r = {
			id: u++,
			callback: i,
			priorityLevel: r,
			startTime: a,
			expirationTime: s,
			sortIndex: -1
		}, a > o ? (r.sortIndex = a, t(l, r), n(c) === null && r === n(l) && (h ? (v(C), C = -1) : h = !0, ie(x, a - o))) : (r.sortIndex = s, t(c, r), m || p || (m = !0, S || (S = !0, E()))), r;
	}, e.unstable_shouldYield = ee, e.unstable_wrapCallback = function(e) {
		var t = f;
		return function() {
			var n = f;
			f = t;
			try {
				return e.apply(this, arguments);
			} finally {
				f = n;
			}
		};
	};
})), o = /* @__PURE__ */ t(((e, t) => {
	t.exports = a();
})), s = /* @__PURE__ */ t(((e) => {
	var t = i();
	function n(e) {
		var t = "https://react.dev/errors/" + e;
		if (1 < arguments.length) {
			t += "?args[]=" + encodeURIComponent(arguments[1]);
			for (var n = 2; n < arguments.length; n++) t += "&args[]=" + encodeURIComponent(arguments[n]);
		}
		return "Minified React error #" + e + "; visit " + t + " for the full message or use the non-minified dev environment for full errors and additional helpful warnings.";
	}
	function r() {}
	var a = {
		d: {
			f: r,
			r: function() {
				throw Error(n(522));
			},
			D: r,
			C: r,
			L: r,
			m: r,
			X: r,
			S: r,
			M: r
		},
		p: 0,
		findDOMNode: null
	}, o = Symbol.for("react.portal");
	function s(e, t, n) {
		var r = 3 < arguments.length && arguments[3] !== void 0 ? arguments[3] : null;
		return {
			$$typeof: o,
			key: r == null ? null : "" + r,
			children: e,
			containerInfo: t,
			implementation: n
		};
	}
	var c = t.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE;
	function l(e, t) {
		if (e === "font") return "";
		if (typeof t == "string") return t === "use-credentials" ? t : "";
	}
	e.__DOM_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE = a, e.createPortal = function(e, t) {
		var r = 2 < arguments.length && arguments[2] !== void 0 ? arguments[2] : null;
		if (!t || t.nodeType !== 1 && t.nodeType !== 9 && t.nodeType !== 11) throw Error(n(299));
		return s(e, t, null, r);
	}, e.flushSync = function(e) {
		var t = c.T, n = a.p;
		try {
			if (c.T = null, a.p = 2, e) return e();
		} finally {
			c.T = t, a.p = n, a.d.f();
		}
	}, e.preconnect = function(e, t) {
		typeof e == "string" && (t ? (t = t.crossOrigin, t = typeof t == "string" ? t === "use-credentials" ? t : "" : void 0) : t = null, a.d.C(e, t));
	}, e.prefetchDNS = function(e) {
		typeof e == "string" && a.d.D(e);
	}, e.preinit = function(e, t) {
		if (typeof e == "string" && t && typeof t.as == "string") {
			var n = t.as, r = l(n, t.crossOrigin), i = typeof t.integrity == "string" ? t.integrity : void 0, o = typeof t.fetchPriority == "string" ? t.fetchPriority : void 0;
			n === "style" ? a.d.S(e, typeof t.precedence == "string" ? t.precedence : void 0, {
				crossOrigin: r,
				integrity: i,
				fetchPriority: o
			}) : n === "script" && a.d.X(e, {
				crossOrigin: r,
				integrity: i,
				fetchPriority: o,
				nonce: typeof t.nonce == "string" ? t.nonce : void 0
			});
		}
	}, e.preinitModule = function(e, t) {
		if (typeof e == "string") if (typeof t == "object" && t) {
			if (t.as == null || t.as === "script") {
				var n = l(t.as, t.crossOrigin);
				a.d.M(e, {
					crossOrigin: n,
					integrity: typeof t.integrity == "string" ? t.integrity : void 0,
					nonce: typeof t.nonce == "string" ? t.nonce : void 0
				});
			}
		} else t ?? a.d.M(e);
	}, e.preload = function(e, t) {
		if (typeof e == "string" && typeof t == "object" && t && typeof t.as == "string") {
			var n = t.as, r = l(n, t.crossOrigin);
			a.d.L(e, n, {
				crossOrigin: r,
				integrity: typeof t.integrity == "string" ? t.integrity : void 0,
				nonce: typeof t.nonce == "string" ? t.nonce : void 0,
				type: typeof t.type == "string" ? t.type : void 0,
				fetchPriority: typeof t.fetchPriority == "string" ? t.fetchPriority : void 0,
				referrerPolicy: typeof t.referrerPolicy == "string" ? t.referrerPolicy : void 0,
				imageSrcSet: typeof t.imageSrcSet == "string" ? t.imageSrcSet : void 0,
				imageSizes: typeof t.imageSizes == "string" ? t.imageSizes : void 0,
				media: typeof t.media == "string" ? t.media : void 0
			});
		}
	}, e.preloadModule = function(e, t) {
		if (typeof e == "string") if (t) {
			var n = l(t.as, t.crossOrigin);
			a.d.m(e, {
				as: typeof t.as == "string" && t.as !== "script" ? t.as : void 0,
				crossOrigin: n,
				integrity: typeof t.integrity == "string" ? t.integrity : void 0
			});
		} else a.d.m(e);
	}, e.requestFormReset = function(e) {
		a.d.r(e);
	}, e.unstable_batchedUpdates = function(e, t) {
		return e(t);
	}, e.useFormState = function(e, t, n) {
		return c.H.useFormState(e, t, n);
	}, e.useFormStatus = function() {
		return c.H.useHostTransitionStatus();
	}, e.version = "19.2.8";
})), c = /* @__PURE__ */ t(((e, t) => {
	function n() {
		if (!(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ > "u" || typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE != "function")) try {
			__REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(n);
		} catch (e) {
			console.error(e);
		}
	}
	n(), t.exports = s();
})), l = /* @__PURE__ */ t(((e) => {
	var t = o(), n = i(), r = c();
	function a(e) {
		var t = "https://react.dev/errors/" + e;
		if (1 < arguments.length) {
			t += "?args[]=" + encodeURIComponent(arguments[1]);
			for (var n = 2; n < arguments.length; n++) t += "&args[]=" + encodeURIComponent(arguments[n]);
		}
		return "Minified React error #" + e + "; visit " + t + " for the full message or use the non-minified dev environment for full errors and additional helpful warnings.";
	}
	function s(e) {
		return !(!e || e.nodeType !== 1 && e.nodeType !== 9 && e.nodeType !== 11);
	}
	function l(e) {
		var t = e, n = e;
		if (e.alternate) for (; t.return;) t = t.return;
		else {
			e = t;
			do
				t = e, t.flags & 4098 && (n = t.return), e = t.return;
			while (e);
		}
		return t.tag === 3 ? n : null;
	}
	function u(e) {
		if (e.tag === 13) {
			var t = e.memoizedState;
			if (t === null && (e = e.alternate, e !== null && (t = e.memoizedState)), t !== null) return t.dehydrated;
		}
		return null;
	}
	function d(e) {
		if (e.tag === 31) {
			var t = e.memoizedState;
			if (t === null && (e = e.alternate, e !== null && (t = e.memoizedState)), t !== null) return t.dehydrated;
		}
		return null;
	}
	function f(e) {
		if (l(e) !== e) throw Error(a(188));
	}
	function p(e) {
		var t = e.alternate;
		if (!t) {
			if (t = l(e), t === null) throw Error(a(188));
			return t === e ? e : null;
		}
		for (var n = e, r = t;;) {
			var i = n.return;
			if (i === null) break;
			var o = i.alternate;
			if (o === null) {
				if (r = i.return, r !== null) {
					n = r;
					continue;
				}
				break;
			}
			if (i.child === o.child) {
				for (o = i.child; o;) {
					if (o === n) return f(i), e;
					if (o === r) return f(i), t;
					o = o.sibling;
				}
				throw Error(a(188));
			}
			if (n.return !== r.return) n = i, r = o;
			else {
				for (var s = !1, c = i.child; c;) {
					if (c === n) {
						s = !0, n = i, r = o;
						break;
					}
					if (c === r) {
						s = !0, r = i, n = o;
						break;
					}
					c = c.sibling;
				}
				if (!s) {
					for (c = o.child; c;) {
						if (c === n) {
							s = !0, n = o, r = i;
							break;
						}
						if (c === r) {
							s = !0, r = o, n = i;
							break;
						}
						c = c.sibling;
					}
					if (!s) throw Error(a(189));
				}
			}
			if (n.alternate !== r) throw Error(a(190));
		}
		if (n.tag !== 3) throw Error(a(188));
		return n.stateNode.current === n ? e : t;
	}
	function m(e) {
		var t = e.tag;
		if (t === 5 || t === 26 || t === 27 || t === 6) return e;
		for (e = e.child; e !== null;) {
			if (t = m(e), t !== null) return t;
			e = e.sibling;
		}
		return null;
	}
	var h = Object.assign, g = Symbol.for("react.element"), _ = Symbol.for("react.transitional.element"), v = Symbol.for("react.portal"), y = Symbol.for("react.fragment"), b = Symbol.for("react.strict_mode"), x = Symbol.for("react.profiler"), S = Symbol.for("react.consumer"), C = Symbol.for("react.context"), w = Symbol.for("react.forward_ref"), T = Symbol.for("react.suspense"), ee = Symbol.for("react.suspense_list"), te = Symbol.for("react.memo"), E = Symbol.for("react.lazy"), ne = Symbol.for("react.activity"), re = Symbol.for("react.memo_cache_sentinel"), ie = Symbol.iterator;
	function ae(e) {
		return typeof e != "object" || !e ? null : (e = ie && e[ie] || e["@@iterator"], typeof e == "function" ? e : null);
	}
	var D = Symbol.for("react.client.reference");
	function oe(e) {
		if (e == null) return null;
		if (typeof e == "function") return e.$$typeof === D ? null : e.displayName || e.name || null;
		if (typeof e == "string") return e;
		switch (e) {
			case y: return "Fragment";
			case x: return "Profiler";
			case b: return "StrictMode";
			case T: return "Suspense";
			case ee: return "SuspenseList";
			case ne: return "Activity";
		}
		if (typeof e == "object") switch (e.$$typeof) {
			case v: return "Portal";
			case C: return e.displayName || "Context";
			case S: return (e._context.displayName || "Context") + ".Consumer";
			case w:
				var t = e.render;
				return e = e.displayName, e ||= (e = t.displayName || t.name || "", e === "" ? "ForwardRef" : "ForwardRef(" + e + ")"), e;
			case te: return t = e.displayName || null, t === null ? oe(e.type) || "Memo" : t;
			case E:
				t = e._payload, e = e._init;
				try {
					return oe(e(t));
				} catch {}
		}
		return null;
	}
	var se = Array.isArray, O = n.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE, k = r.__DOM_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE, ce = {
		pending: !1,
		data: null,
		method: null,
		action: null
	}, le = [], ue = -1;
	function de(e) {
		return { current: e };
	}
	function A(e) {
		0 > ue || (e.current = le[ue], le[ue] = null, ue--);
	}
	function j(e, t) {
		ue++, le[ue] = e.current, e.current = t;
	}
	var fe = de(null), pe = de(null), me = de(null), he = de(null);
	function ge(e, t) {
		switch (j(me, t), j(pe, e), j(fe, null), t.nodeType) {
			case 9:
			case 11:
				e = (e = t.documentElement) && (e = e.namespaceURI) ? Vd(e) : 0;
				break;
			default: if (e = t.tagName, t = t.namespaceURI) t = Vd(t), e = Hd(t, e);
			else switch (e) {
				case "svg":
					e = 1;
					break;
				case "math":
					e = 2;
					break;
				default: e = 0;
			}
		}
		A(fe), j(fe, e);
	}
	function _e() {
		A(fe), A(pe), A(me);
	}
	function ve(e) {
		e.memoizedState !== null && j(he, e);
		var t = fe.current, n = Hd(t, e.type);
		t !== n && (j(pe, e), j(fe, n));
	}
	function ye(e) {
		pe.current === e && (A(fe), A(pe)), he.current === e && (A(he), Qf._currentValue = ce);
	}
	var be, xe;
	function Se(e) {
		if (be === void 0) try {
			throw Error();
		} catch (e) {
			var t = e.stack.trim().match(/\n( *(at )?)/);
			be = t && t[1] || "", xe = -1 < e.stack.indexOf("\n    at") ? " (<anonymous>)" : -1 < e.stack.indexOf("@") ? "@unknown:0:0" : "";
		}
		return "\n" + be + e + xe;
	}
	var Ce = !1;
	function we(e, t) {
		if (!e || Ce) return "";
		Ce = !0;
		var n = Error.prepareStackTrace;
		Error.prepareStackTrace = void 0;
		try {
			var r = { DetermineComponentFrameRoot: function() {
				try {
					if (t) {
						var n = function() {
							throw Error();
						};
						if (Object.defineProperty(n.prototype, "props", { set: function() {
							throw Error();
						} }), typeof Reflect == "object" && Reflect.construct) {
							try {
								Reflect.construct(n, []);
							} catch (e) {
								var r = e;
							}
							Reflect.construct(e, [], n);
						} else {
							try {
								n.call();
							} catch (e) {
								r = e;
							}
							e.call(n.prototype);
						}
					} else {
						try {
							throw Error();
						} catch (e) {
							r = e;
						}
						(n = e()) && typeof n.catch == "function" && n.catch(function() {});
					}
				} catch (e) {
					if (e && r && typeof e.stack == "string") return [e.stack, r.stack];
				}
				return [null, null];
			} };
			r.DetermineComponentFrameRoot.displayName = "DetermineComponentFrameRoot";
			var i = Object.getOwnPropertyDescriptor(r.DetermineComponentFrameRoot, "name");
			i && i.configurable && Object.defineProperty(r.DetermineComponentFrameRoot, "name", { value: "DetermineComponentFrameRoot" });
			var a = r.DetermineComponentFrameRoot(), o = a[0], s = a[1];
			if (o && s) {
				var c = o.split("\n"), l = s.split("\n");
				for (i = r = 0; r < c.length && !c[r].includes("DetermineComponentFrameRoot");) r++;
				for (; i < l.length && !l[i].includes("DetermineComponentFrameRoot");) i++;
				if (r === c.length || i === l.length) for (r = c.length - 1, i = l.length - 1; 1 <= r && 0 <= i && c[r] !== l[i];) i--;
				for (; 1 <= r && 0 <= i; r--, i--) if (c[r] !== l[i]) {
					if (r !== 1 || i !== 1) do
						if (r--, i--, 0 > i || c[r] !== l[i]) {
							var u = "\n" + c[r].replace(" at new ", " at ");
							return e.displayName && u.includes("<anonymous>") && (u = u.replace("<anonymous>", e.displayName)), u;
						}
					while (1 <= r && 0 <= i);
					break;
				}
			}
		} finally {
			Ce = !1, Error.prepareStackTrace = n;
		}
		return (n = e ? e.displayName || e.name : "") ? Se(n) : "";
	}
	function Te(e, t) {
		switch (e.tag) {
			case 26:
			case 27:
			case 5: return Se(e.type);
			case 16: return Se("Lazy");
			case 13: return e.child !== t && t !== null ? Se("Suspense Fallback") : Se("Suspense");
			case 19: return Se("SuspenseList");
			case 0:
			case 15: return we(e.type, !1);
			case 11: return we(e.type.render, !1);
			case 1: return we(e.type, !0);
			case 31: return Se("Activity");
			default: return "";
		}
	}
	function Ee(e) {
		try {
			var t = "", n = null;
			do
				t += Te(e, n), n = e, e = e.return;
			while (e);
			return t;
		} catch (e) {
			return "\nError generating stack: " + e.message + "\n" + e.stack;
		}
	}
	var De = Object.prototype.hasOwnProperty, M = t.unstable_scheduleCallback, Oe = t.unstable_cancelCallback, ke = t.unstable_shouldYield, Ae = t.unstable_requestPaint, je = t.unstable_now, Me = t.unstable_getCurrentPriorityLevel, Ne = t.unstable_ImmediatePriority, Pe = t.unstable_UserBlockingPriority, Fe = t.unstable_NormalPriority, Ie = t.unstable_LowPriority, Le = t.unstable_IdlePriority, Re = t.log, ze = t.unstable_setDisableYieldValue, Be = null, Ve = null;
	function He(e) {
		if (typeof Re == "function" && ze(e), Ve && typeof Ve.setStrictMode == "function") try {
			Ve.setStrictMode(Be, e);
		} catch {}
	}
	var Ue = Math.clz32 ? Math.clz32 : Ke, We = Math.log, Ge = Math.LN2;
	function Ke(e) {
		return e >>>= 0, e === 0 ? 32 : 31 - (We(e) / Ge | 0) | 0;
	}
	var qe = 256, Je = 262144, Ye = 4194304;
	function Xe(e) {
		var t = e & 42;
		if (t !== 0) return t;
		switch (e & -e) {
			case 1: return 1;
			case 2: return 2;
			case 4: return 4;
			case 8: return 8;
			case 16: return 16;
			case 32: return 32;
			case 64: return 64;
			case 128: return 128;
			case 256:
			case 512:
			case 1024:
			case 2048:
			case 4096:
			case 8192:
			case 16384:
			case 32768:
			case 65536:
			case 131072: return e & 261888;
			case 262144:
			case 524288:
			case 1048576:
			case 2097152: return e & 3932160;
			case 4194304:
			case 8388608:
			case 16777216:
			case 33554432: return e & 62914560;
			case 67108864: return 67108864;
			case 134217728: return 134217728;
			case 268435456: return 268435456;
			case 536870912: return 536870912;
			case 1073741824: return 0;
			default: return e;
		}
	}
	function Ze(e, t, n) {
		var r = e.pendingLanes;
		if (r === 0) return 0;
		var i = 0, a = e.suspendedLanes, o = e.pingedLanes;
		e = e.warmLanes;
		var s = r & 134217727;
		return s === 0 ? (s = r & ~a, s === 0 ? o === 0 ? n || (n = r & ~e, n !== 0 && (i = Xe(n))) : i = Xe(o) : i = Xe(s)) : (r = s & ~a, r === 0 ? (o &= s, o === 0 ? n || (n = s & ~e, n !== 0 && (i = Xe(n))) : i = Xe(o)) : i = Xe(r)), i === 0 ? 0 : t !== 0 && t !== i && (t & a) === 0 && (a = i & -i, n = t & -t, a >= n || a === 32 && n & 4194048) ? t : i;
	}
	function Qe(e, t) {
		return (e.pendingLanes & ~(e.suspendedLanes & ~e.pingedLanes) & t) === 0;
	}
	function $e(e, t) {
		switch (e) {
			case 1:
			case 2:
			case 4:
			case 8:
			case 64: return t + 250;
			case 16:
			case 32:
			case 128:
			case 256:
			case 512:
			case 1024:
			case 2048:
			case 4096:
			case 8192:
			case 16384:
			case 32768:
			case 65536:
			case 131072:
			case 262144:
			case 524288:
			case 1048576:
			case 2097152: return t + 5e3;
			case 4194304:
			case 8388608:
			case 16777216:
			case 33554432: return -1;
			case 67108864:
			case 134217728:
			case 268435456:
			case 536870912:
			case 1073741824: return -1;
			default: return -1;
		}
	}
	function et() {
		var e = Ye;
		return Ye <<= 1, !(Ye & 62914560) && (Ye = 4194304), e;
	}
	function tt(e) {
		for (var t = [], n = 0; 31 > n; n++) t.push(e);
		return t;
	}
	function nt(e, t) {
		e.pendingLanes |= t, t !== 268435456 && (e.suspendedLanes = 0, e.pingedLanes = 0, e.warmLanes = 0);
	}
	function rt(e, t, n, r, i, a) {
		var o = e.pendingLanes;
		e.pendingLanes = n, e.suspendedLanes = 0, e.pingedLanes = 0, e.warmLanes = 0, e.expiredLanes &= n, e.entangledLanes &= n, e.errorRecoveryDisabledLanes &= n, e.shellSuspendCounter = 0;
		var s = e.entanglements, c = e.expirationTimes, l = e.hiddenUpdates;
		for (n = o & ~n; 0 < n;) {
			var u = 31 - Ue(n), d = 1 << u;
			s[u] = 0, c[u] = -1;
			var f = l[u];
			if (f !== null) for (l[u] = null, u = 0; u < f.length; u++) {
				var p = f[u];
				p !== null && (p.lane &= -536870913);
			}
			n &= ~d;
		}
		r !== 0 && it(e, r, 0), a !== 0 && i === 0 && e.tag !== 0 && (e.suspendedLanes |= a & ~(o & ~t));
	}
	function it(e, t, n) {
		e.pendingLanes |= t, e.suspendedLanes &= ~t;
		var r = 31 - Ue(t);
		e.entangledLanes |= t, e.entanglements[r] = e.entanglements[r] | 1073741824 | n & 261930;
	}
	function at(e, t) {
		var n = e.entangledLanes |= t;
		for (e = e.entanglements; n;) {
			var r = 31 - Ue(n), i = 1 << r;
			i & t | e[r] & t && (e[r] |= t), n &= ~i;
		}
	}
	function ot(e, t) {
		var n = t & -t;
		return n = n & 42 ? 1 : st(n), (n & (e.suspendedLanes | t)) === 0 ? n : 0;
	}
	function st(e) {
		switch (e) {
			case 2:
				e = 1;
				break;
			case 8:
				e = 4;
				break;
			case 32:
				e = 16;
				break;
			case 256:
			case 512:
			case 1024:
			case 2048:
			case 4096:
			case 8192:
			case 16384:
			case 32768:
			case 65536:
			case 131072:
			case 262144:
			case 524288:
			case 1048576:
			case 2097152:
			case 4194304:
			case 8388608:
			case 16777216:
			case 33554432:
				e = 128;
				break;
			case 268435456:
				e = 134217728;
				break;
			default: e = 0;
		}
		return e;
	}
	function ct(e) {
		return e &= -e, 2 < e ? 8 < e ? e & 134217727 ? 32 : 268435456 : 8 : 2;
	}
	function lt() {
		var e = k.p;
		return e === 0 ? (e = window.event, e === void 0 ? 32 : mp(e.type)) : e;
	}
	function ut(e, t) {
		var n = k.p;
		try {
			return k.p = e, t();
		} finally {
			k.p = n;
		}
	}
	var dt = Math.random().toString(36).slice(2), ft = "__reactFiber$" + dt, pt = "__reactProps$" + dt, mt = "__reactContainer$" + dt, ht = "__reactEvents$" + dt, gt = "__reactListeners$" + dt, _t = "__reactHandles$" + dt, vt = "__reactResources$" + dt, yt = "__reactMarker$" + dt;
	function bt(e) {
		delete e[ft], delete e[pt], delete e[ht], delete e[gt], delete e[_t];
	}
	function xt(e) {
		var t = e[ft];
		if (t) return t;
		for (var n = e.parentNode; n;) {
			if (t = n[mt] || n[ft]) {
				if (n = t.alternate, t.child !== null || n !== null && n.child !== null) for (e = df(e); e !== null;) {
					if (n = e[ft]) return n;
					e = df(e);
				}
				return t;
			}
			e = n, n = e.parentNode;
		}
		return null;
	}
	function N(e) {
		if (e = e[ft] || e[mt]) {
			var t = e.tag;
			if (t === 5 || t === 6 || t === 13 || t === 31 || t === 26 || t === 27 || t === 3) return e;
		}
		return null;
	}
	function St(e) {
		var t = e.tag;
		if (t === 5 || t === 26 || t === 27 || t === 6) return e.stateNode;
		throw Error(a(33));
	}
	function P(e) {
		var t = e[vt];
		return t ||= e[vt] = {
			hoistableStyles: /* @__PURE__ */ new Map(),
			hoistableScripts: /* @__PURE__ */ new Map()
		}, t;
	}
	function Ct(e) {
		e[yt] = !0;
	}
	var wt = /* @__PURE__ */ new Set(), Tt = {};
	function Et(e, t) {
		Dt(e, t), Dt(e + "Capture", t);
	}
	function Dt(e, t) {
		for (Tt[e] = t, e = 0; e < t.length; e++) wt.add(t[e]);
	}
	var Ot = RegExp("^[:A-Z_a-z\\u00C0-\\u00D6\\u00D8-\\u00F6\\u00F8-\\u02FF\\u0370-\\u037D\\u037F-\\u1FFF\\u200C-\\u200D\\u2070-\\u218F\\u2C00-\\u2FEF\\u3001-\\uD7FF\\uF900-\\uFDCF\\uFDF0-\\uFFFD][:A-Z_a-z\\u00C0-\\u00D6\\u00D8-\\u00F6\\u00F8-\\u02FF\\u0370-\\u037D\\u037F-\\u1FFF\\u200C-\\u200D\\u2070-\\u218F\\u2C00-\\u2FEF\\u3001-\\uD7FF\\uF900-\\uFDCF\\uFDF0-\\uFFFD\\-.0-9\\u00B7\\u0300-\\u036F\\u203F-\\u2040]*$"), kt = {}, At = {};
	function jt(e) {
		return De.call(At, e) ? !0 : De.call(kt, e) ? !1 : Ot.test(e) ? At[e] = !0 : (kt[e] = !0, !1);
	}
	function Mt(e, t, n) {
		if (jt(t)) if (n === null) e.removeAttribute(t);
		else {
			switch (typeof n) {
				case "undefined":
				case "function":
				case "symbol":
					e.removeAttribute(t);
					return;
				case "boolean":
					var r = t.toLowerCase().slice(0, 5);
					if (r !== "data-" && r !== "aria-") {
						e.removeAttribute(t);
						return;
					}
			}
			e.setAttribute(t, "" + n);
		}
	}
	function Nt(e, t, n) {
		if (n === null) e.removeAttribute(t);
		else {
			switch (typeof n) {
				case "undefined":
				case "function":
				case "symbol":
				case "boolean":
					e.removeAttribute(t);
					return;
			}
			e.setAttribute(t, "" + n);
		}
	}
	function Pt(e, t, n, r) {
		if (r === null) e.removeAttribute(n);
		else {
			switch (typeof r) {
				case "undefined":
				case "function":
				case "symbol":
				case "boolean":
					e.removeAttribute(n);
					return;
			}
			e.setAttributeNS(t, n, "" + r);
		}
	}
	function Ft(e) {
		switch (typeof e) {
			case "bigint":
			case "boolean":
			case "number":
			case "string":
			case "undefined": return e;
			case "object": return e;
			default: return "";
		}
	}
	function It(e) {
		var t = e.type;
		return (e = e.nodeName) && e.toLowerCase() === "input" && (t === "checkbox" || t === "radio");
	}
	function Lt(e, t, n) {
		var r = Object.getOwnPropertyDescriptor(e.constructor.prototype, t);
		if (!e.hasOwnProperty(t) && r !== void 0 && typeof r.get == "function" && typeof r.set == "function") {
			var i = r.get, a = r.set;
			return Object.defineProperty(e, t, {
				configurable: !0,
				get: function() {
					return i.call(this);
				},
				set: function(e) {
					n = "" + e, a.call(this, e);
				}
			}), Object.defineProperty(e, t, { enumerable: r.enumerable }), {
				getValue: function() {
					return n;
				},
				setValue: function(e) {
					n = "" + e;
				},
				stopTracking: function() {
					e._valueTracker = null, delete e[t];
				}
			};
		}
	}
	function Rt(e) {
		if (!e._valueTracker) {
			var t = It(e) ? "checked" : "value";
			e._valueTracker = Lt(e, t, "" + e[t]);
		}
	}
	function zt(e) {
		if (!e) return !1;
		var t = e._valueTracker;
		if (!t) return !0;
		var n = t.getValue(), r = "";
		return e && (r = It(e) ? e.checked ? "true" : "false" : e.value), e = r, e === n ? !1 : (t.setValue(e), !0);
	}
	function Bt(e) {
		if (e ||= typeof document < "u" ? document : void 0, e === void 0) return null;
		try {
			return e.activeElement || e.body;
		} catch {
			return e.body;
		}
	}
	var Vt = /[\n"\\]/g;
	function Ht(e) {
		return e.replace(Vt, function(e) {
			return "\\" + e.charCodeAt(0).toString(16) + " ";
		});
	}
	function Ut(e, t, n, r, i, a, o, s) {
		e.name = "", o != null && typeof o != "function" && typeof o != "symbol" && typeof o != "boolean" ? e.type = o : e.removeAttribute("type"), t == null ? o !== "submit" && o !== "reset" || e.removeAttribute("value") : o === "number" ? (t === 0 && e.value === "" || e.value != t) && (e.value = "" + Ft(t)) : e.value !== "" + Ft(t) && (e.value = "" + Ft(t)), t == null ? n == null ? r != null && e.removeAttribute("value") : Gt(e, o, Ft(n)) : Gt(e, o, Ft(t)), i == null && a != null && (e.defaultChecked = !!a), i != null && (e.checked = i && typeof i != "function" && typeof i != "symbol"), s != null && typeof s != "function" && typeof s != "symbol" && typeof s != "boolean" ? e.name = "" + Ft(s) : e.removeAttribute("name");
	}
	function Wt(e, t, n, r, i, a, o, s) {
		if (a != null && typeof a != "function" && typeof a != "symbol" && typeof a != "boolean" && (e.type = a), t != null || n != null) {
			if (!(a !== "submit" && a !== "reset" || t != null)) {
				Rt(e);
				return;
			}
			n = n == null ? "" : "" + Ft(n), t = t == null ? n : "" + Ft(t), s || t === e.value || (e.value = t), e.defaultValue = t;
		}
		r ??= i, r = typeof r != "function" && typeof r != "symbol" && !!r, e.checked = s ? e.checked : !!r, e.defaultChecked = !!r, o != null && typeof o != "function" && typeof o != "symbol" && typeof o != "boolean" && (e.name = o), Rt(e);
	}
	function Gt(e, t, n) {
		t === "number" && Bt(e.ownerDocument) === e || e.defaultValue === "" + n || (e.defaultValue = "" + n);
	}
	function Kt(e, t, n, r) {
		if (e = e.options, t) {
			t = {};
			for (var i = 0; i < n.length; i++) t["$" + n[i]] = !0;
			for (n = 0; n < e.length; n++) i = t.hasOwnProperty("$" + e[n].value), e[n].selected !== i && (e[n].selected = i), i && r && (e[n].defaultSelected = !0);
		} else {
			for (n = "" + Ft(n), t = null, i = 0; i < e.length; i++) {
				if (e[i].value === n) {
					e[i].selected = !0, r && (e[i].defaultSelected = !0);
					return;
				}
				t !== null || e[i].disabled || (t = e[i]);
			}
			t !== null && (t.selected = !0);
		}
	}
	function qt(e, t, n) {
		if (t != null && (t = "" + Ft(t), t !== e.value && (e.value = t), n == null)) {
			e.defaultValue !== t && (e.defaultValue = t);
			return;
		}
		e.defaultValue = n == null ? "" : "" + Ft(n);
	}
	function Jt(e, t, n, r) {
		if (t == null) {
			if (r != null) {
				if (n != null) throw Error(a(92));
				if (se(r)) {
					if (1 < r.length) throw Error(a(93));
					r = r[0];
				}
				n = r;
			}
			n ??= "", t = n;
		}
		n = Ft(t), e.defaultValue = n, r = e.textContent, r === n && r !== "" && r !== null && (e.value = r), Rt(e);
	}
	function Yt(e, t) {
		if (t) {
			var n = e.firstChild;
			if (n && n === e.lastChild && n.nodeType === 3) {
				n.nodeValue = t;
				return;
			}
		}
		e.textContent = t;
	}
	var Xt = new Set("animationIterationCount aspectRatio borderImageOutset borderImageSlice borderImageWidth boxFlex boxFlexGroup boxOrdinalGroup columnCount columns flex flexGrow flexPositive flexShrink flexNegative flexOrder gridArea gridRow gridRowEnd gridRowSpan gridRowStart gridColumn gridColumnEnd gridColumnSpan gridColumnStart fontWeight lineClamp lineHeight opacity order orphans scale tabSize widows zIndex zoom fillOpacity floodOpacity stopOpacity strokeDasharray strokeDashoffset strokeMiterlimit strokeOpacity strokeWidth MozAnimationIterationCount MozBoxFlex MozBoxFlexGroup MozLineClamp msAnimationIterationCount msFlex msZoom msFlexGrow msFlexNegative msFlexOrder msFlexPositive msFlexShrink msGridColumn msGridColumnSpan msGridRow msGridRowSpan WebkitAnimationIterationCount WebkitBoxFlex WebKitBoxFlexGroup WebkitBoxOrdinalGroup WebkitColumnCount WebkitColumns WebkitFlex WebkitFlexGrow WebkitFlexPositive WebkitFlexShrink WebkitLineClamp".split(" "));
	function Zt(e, t, n) {
		var r = t.indexOf("--") === 0;
		n == null || typeof n == "boolean" || n === "" ? r ? e.setProperty(t, "") : t === "float" ? e.cssFloat = "" : e[t] = "" : r ? e.setProperty(t, n) : typeof n != "number" || n === 0 || Xt.has(t) ? t === "float" ? e.cssFloat = n : e[t] = ("" + n).trim() : e[t] = n + "px";
	}
	function Qt(e, t, n) {
		if (t != null && typeof t != "object") throw Error(a(62));
		if (e = e.style, n != null) {
			for (var r in n) !n.hasOwnProperty(r) || t != null && t.hasOwnProperty(r) || (r.indexOf("--") === 0 ? e.setProperty(r, "") : r === "float" ? e.cssFloat = "" : e[r] = "");
			for (var i in t) r = t[i], t.hasOwnProperty(i) && n[i] !== r && Zt(e, i, r);
		} else for (var o in t) t.hasOwnProperty(o) && Zt(e, o, t[o]);
	}
	function $t(e) {
		if (e.indexOf("-") === -1) return !1;
		switch (e) {
			case "annotation-xml":
			case "color-profile":
			case "font-face":
			case "font-face-src":
			case "font-face-uri":
			case "font-face-format":
			case "font-face-name":
			case "missing-glyph": return !1;
			default: return !0;
		}
	}
	var en = /* @__PURE__ */ new Map([
		["acceptCharset", "accept-charset"],
		["htmlFor", "for"],
		["httpEquiv", "http-equiv"],
		["crossOrigin", "crossorigin"],
		["accentHeight", "accent-height"],
		["alignmentBaseline", "alignment-baseline"],
		["arabicForm", "arabic-form"],
		["baselineShift", "baseline-shift"],
		["capHeight", "cap-height"],
		["clipPath", "clip-path"],
		["clipRule", "clip-rule"],
		["colorInterpolation", "color-interpolation"],
		["colorInterpolationFilters", "color-interpolation-filters"],
		["colorProfile", "color-profile"],
		["colorRendering", "color-rendering"],
		["dominantBaseline", "dominant-baseline"],
		["enableBackground", "enable-background"],
		["fillOpacity", "fill-opacity"],
		["fillRule", "fill-rule"],
		["floodColor", "flood-color"],
		["floodOpacity", "flood-opacity"],
		["fontFamily", "font-family"],
		["fontSize", "font-size"],
		["fontSizeAdjust", "font-size-adjust"],
		["fontStretch", "font-stretch"],
		["fontStyle", "font-style"],
		["fontVariant", "font-variant"],
		["fontWeight", "font-weight"],
		["glyphName", "glyph-name"],
		["glyphOrientationHorizontal", "glyph-orientation-horizontal"],
		["glyphOrientationVertical", "glyph-orientation-vertical"],
		["horizAdvX", "horiz-adv-x"],
		["horizOriginX", "horiz-origin-x"],
		["imageRendering", "image-rendering"],
		["letterSpacing", "letter-spacing"],
		["lightingColor", "lighting-color"],
		["markerEnd", "marker-end"],
		["markerMid", "marker-mid"],
		["markerStart", "marker-start"],
		["overlinePosition", "overline-position"],
		["overlineThickness", "overline-thickness"],
		["paintOrder", "paint-order"],
		["panose-1", "panose-1"],
		["pointerEvents", "pointer-events"],
		["renderingIntent", "rendering-intent"],
		["shapeRendering", "shape-rendering"],
		["stopColor", "stop-color"],
		["stopOpacity", "stop-opacity"],
		["strikethroughPosition", "strikethrough-position"],
		["strikethroughThickness", "strikethrough-thickness"],
		["strokeDasharray", "stroke-dasharray"],
		["strokeDashoffset", "stroke-dashoffset"],
		["strokeLinecap", "stroke-linecap"],
		["strokeLinejoin", "stroke-linejoin"],
		["strokeMiterlimit", "stroke-miterlimit"],
		["strokeOpacity", "stroke-opacity"],
		["strokeWidth", "stroke-width"],
		["textAnchor", "text-anchor"],
		["textDecoration", "text-decoration"],
		["textRendering", "text-rendering"],
		["transformOrigin", "transform-origin"],
		["underlinePosition", "underline-position"],
		["underlineThickness", "underline-thickness"],
		["unicodeBidi", "unicode-bidi"],
		["unicodeRange", "unicode-range"],
		["unitsPerEm", "units-per-em"],
		["vAlphabetic", "v-alphabetic"],
		["vHanging", "v-hanging"],
		["vIdeographic", "v-ideographic"],
		["vMathematical", "v-mathematical"],
		["vectorEffect", "vector-effect"],
		["vertAdvY", "vert-adv-y"],
		["vertOriginX", "vert-origin-x"],
		["vertOriginY", "vert-origin-y"],
		["wordSpacing", "word-spacing"],
		["writingMode", "writing-mode"],
		["xmlnsXlink", "xmlns:xlink"],
		["xHeight", "x-height"]
	]), tn = /^[\u0000-\u001F ]*j[\r\n\t]*a[\r\n\t]*v[\r\n\t]*a[\r\n\t]*s[\r\n\t]*c[\r\n\t]*r[\r\n\t]*i[\r\n\t]*p[\r\n\t]*t[\r\n\t]*:/i;
	function nn(e) {
		return tn.test("" + e) ? "javascript:throw new Error('React has blocked a javascript: URL as a security precaution.')" : e;
	}
	function F() {}
	var rn = null;
	function an(e) {
		return e = e.target || e.srcElement || window, e.correspondingUseElement && (e = e.correspondingUseElement), e.nodeType === 3 ? e.parentNode : e;
	}
	var on = null, sn = null;
	function cn(e) {
		var t = N(e);
		if (t && (e = t.stateNode)) {
			var n = e[pt] || null;
			a: switch (e = t.stateNode, t.type) {
				case "input":
					if (Ut(e, n.value, n.defaultValue, n.defaultValue, n.checked, n.defaultChecked, n.type, n.name), t = n.name, n.type === "radio" && t != null) {
						for (n = e; n.parentNode;) n = n.parentNode;
						for (n = n.querySelectorAll("input[name=\"" + Ht("" + t) + "\"][type=\"radio\"]"), t = 0; t < n.length; t++) {
							var r = n[t];
							if (r !== e && r.form === e.form) {
								var i = r[pt] || null;
								if (!i) throw Error(a(90));
								Ut(r, i.value, i.defaultValue, i.defaultValue, i.checked, i.defaultChecked, i.type, i.name);
							}
						}
						for (t = 0; t < n.length; t++) r = n[t], r.form === e.form && zt(r);
					}
					break a;
				case "textarea":
					qt(e, n.value, n.defaultValue);
					break a;
				case "select": t = n.value, t != null && Kt(e, !!n.multiple, t, !1);
			}
		}
	}
	var ln = !1;
	function un(e, t, n) {
		if (ln) return e(t, n);
		ln = !0;
		try {
			return e(t);
		} finally {
			if (ln = !1, (on !== null || sn !== null) && (bu(), on && (t = on, e = sn, sn = on = null, cn(t), e))) for (t = 0; t < e.length; t++) cn(e[t]);
		}
	}
	function dn(e, t) {
		var n = e.stateNode;
		if (n === null) return null;
		var r = n[pt] || null;
		if (r === null) return null;
		n = r[t];
		a: switch (t) {
			case "onClick":
			case "onClickCapture":
			case "onDoubleClick":
			case "onDoubleClickCapture":
			case "onMouseDown":
			case "onMouseDownCapture":
			case "onMouseMove":
			case "onMouseMoveCapture":
			case "onMouseUp":
			case "onMouseUpCapture":
			case "onMouseEnter":
				(r = !r.disabled) || (e = e.type, r = !(e === "button" || e === "input" || e === "select" || e === "textarea")), e = !r;
				break a;
			default: e = !1;
		}
		if (e) return null;
		if (n && typeof n != "function") throw Error(a(231, t, typeof n));
		return n;
	}
	var fn = !(typeof window > "u" || window.document === void 0 || window.document.createElement === void 0), pn = !1;
	if (fn) try {
		var mn = {};
		Object.defineProperty(mn, "passive", { get: function() {
			pn = !0;
		} }), window.addEventListener("test", mn, mn), window.removeEventListener("test", mn, mn);
	} catch {
		pn = !1;
	}
	var hn = null, gn = null, I = null;
	function _n() {
		if (I) return I;
		var e, t = gn, n = t.length, r, i = "value" in hn ? hn.value : hn.textContent, a = i.length;
		for (e = 0; e < n && t[e] === i[e]; e++);
		var o = n - e;
		for (r = 1; r <= o && t[n - r] === i[a - r]; r++);
		return I = i.slice(e, 1 < r ? 1 - r : void 0);
	}
	function L(e) {
		var t = e.keyCode;
		return "charCode" in e ? (e = e.charCode, e === 0 && t === 13 && (e = 13)) : e = t, e === 10 && (e = 13), 32 <= e || e === 13 ? e : 0;
	}
	function vn() {
		return !0;
	}
	function yn() {
		return !1;
	}
	function bn(e) {
		function t(t, n, r, i, a) {
			for (var o in this._reactName = t, this._targetInst = r, this.type = n, this.nativeEvent = i, this.target = a, this.currentTarget = null, e) e.hasOwnProperty(o) && (t = e[o], this[o] = t ? t(i) : i[o]);
			return this.isDefaultPrevented = (i.defaultPrevented == null ? !1 === i.returnValue : i.defaultPrevented) ? vn : yn, this.isPropagationStopped = yn, this;
		}
		return h(t.prototype, {
			preventDefault: function() {
				this.defaultPrevented = !0;
				var e = this.nativeEvent;
				e && (e.preventDefault ? e.preventDefault() : typeof e.returnValue != "unknown" && (e.returnValue = !1), this.isDefaultPrevented = vn);
			},
			stopPropagation: function() {
				var e = this.nativeEvent;
				e && (e.stopPropagation ? e.stopPropagation() : typeof e.cancelBubble != "unknown" && (e.cancelBubble = !0), this.isPropagationStopped = vn);
			},
			persist: function() {},
			isPersistent: vn
		}), t;
	}
	var xn = {
		eventPhase: 0,
		bubbles: 0,
		cancelable: 0,
		timeStamp: function(e) {
			return e.timeStamp || Date.now();
		},
		defaultPrevented: 0,
		isTrusted: 0
	}, Sn = bn(xn), Cn = h({}, xn, {
		view: 0,
		detail: 0
	}), wn = bn(Cn), Tn, En, Dn, On = h({}, Cn, {
		screenX: 0,
		screenY: 0,
		clientX: 0,
		clientY: 0,
		pageX: 0,
		pageY: 0,
		ctrlKey: 0,
		shiftKey: 0,
		altKey: 0,
		metaKey: 0,
		getModifierState: zn,
		button: 0,
		buttons: 0,
		relatedTarget: function(e) {
			return e.relatedTarget === void 0 ? e.fromElement === e.srcElement ? e.toElement : e.fromElement : e.relatedTarget;
		},
		movementX: function(e) {
			return "movementX" in e ? e.movementX : (e !== Dn && (Dn && e.type === "mousemove" ? (Tn = e.screenX - Dn.screenX, En = e.screenY - Dn.screenY) : En = Tn = 0, Dn = e), Tn);
		},
		movementY: function(e) {
			return "movementY" in e ? e.movementY : En;
		}
	}), kn = bn(On), An = bn(h({}, On, { dataTransfer: 0 })), jn = bn(h({}, Cn, { relatedTarget: 0 })), Mn = bn(h({}, xn, {
		animationName: 0,
		elapsedTime: 0,
		pseudoElement: 0
	})), Nn = bn(h({}, xn, { clipboardData: function(e) {
		return "clipboardData" in e ? e.clipboardData : window.clipboardData;
	} })), Pn = bn(h({}, xn, { data: 0 })), Fn = {
		Esc: "Escape",
		Spacebar: " ",
		Left: "ArrowLeft",
		Up: "ArrowUp",
		Right: "ArrowRight",
		Down: "ArrowDown",
		Del: "Delete",
		Win: "OS",
		Menu: "ContextMenu",
		Apps: "ContextMenu",
		Scroll: "ScrollLock",
		MozPrintableKey: "Unidentified"
	}, In = {
		8: "Backspace",
		9: "Tab",
		12: "Clear",
		13: "Enter",
		16: "Shift",
		17: "Control",
		18: "Alt",
		19: "Pause",
		20: "CapsLock",
		27: "Escape",
		32: " ",
		33: "PageUp",
		34: "PageDown",
		35: "End",
		36: "Home",
		37: "ArrowLeft",
		38: "ArrowUp",
		39: "ArrowRight",
		40: "ArrowDown",
		45: "Insert",
		46: "Delete",
		112: "F1",
		113: "F2",
		114: "F3",
		115: "F4",
		116: "F5",
		117: "F6",
		118: "F7",
		119: "F8",
		120: "F9",
		121: "F10",
		122: "F11",
		123: "F12",
		144: "NumLock",
		145: "ScrollLock",
		224: "Meta"
	}, Ln = {
		Alt: "altKey",
		Control: "ctrlKey",
		Meta: "metaKey",
		Shift: "shiftKey"
	};
	function Rn(e) {
		var t = this.nativeEvent;
		return t.getModifierState ? t.getModifierState(e) : (e = Ln[e]) ? !!t[e] : !1;
	}
	function zn() {
		return Rn;
	}
	var Bn = bn(h({}, Cn, {
		key: function(e) {
			if (e.key) {
				var t = Fn[e.key] || e.key;
				if (t !== "Unidentified") return t;
			}
			return e.type === "keypress" ? (e = L(e), e === 13 ? "Enter" : String.fromCharCode(e)) : e.type === "keydown" || e.type === "keyup" ? In[e.keyCode] || "Unidentified" : "";
		},
		code: 0,
		location: 0,
		ctrlKey: 0,
		shiftKey: 0,
		altKey: 0,
		metaKey: 0,
		repeat: 0,
		locale: 0,
		getModifierState: zn,
		charCode: function(e) {
			return e.type === "keypress" ? L(e) : 0;
		},
		keyCode: function(e) {
			return e.type === "keydown" || e.type === "keyup" ? e.keyCode : 0;
		},
		which: function(e) {
			return e.type === "keypress" ? L(e) : e.type === "keydown" || e.type === "keyup" ? e.keyCode : 0;
		}
	})), Vn = bn(h({}, On, {
		pointerId: 0,
		width: 0,
		height: 0,
		pressure: 0,
		tangentialPressure: 0,
		tiltX: 0,
		tiltY: 0,
		twist: 0,
		pointerType: 0,
		isPrimary: 0
	})), Hn = bn(h({}, Cn, {
		touches: 0,
		targetTouches: 0,
		changedTouches: 0,
		altKey: 0,
		metaKey: 0,
		ctrlKey: 0,
		shiftKey: 0,
		getModifierState: zn
	})), Un = bn(h({}, xn, {
		propertyName: 0,
		elapsedTime: 0,
		pseudoElement: 0
	})), Wn = bn(h({}, On, {
		deltaX: function(e) {
			return "deltaX" in e ? e.deltaX : "wheelDeltaX" in e ? -e.wheelDeltaX : 0;
		},
		deltaY: function(e) {
			return "deltaY" in e ? e.deltaY : "wheelDeltaY" in e ? -e.wheelDeltaY : "wheelDelta" in e ? -e.wheelDelta : 0;
		},
		deltaZ: 0,
		deltaMode: 0
	})), Gn = bn(h({}, xn, {
		newState: 0,
		oldState: 0
	})), Kn = [
		9,
		13,
		27,
		32
	], qn = fn && "CompositionEvent" in window, Jn = null;
	fn && "documentMode" in document && (Jn = document.documentMode);
	var Yn = fn && "TextEvent" in window && !Jn, Xn = fn && (!qn || Jn && 8 < Jn && 11 >= Jn), Zn = " ", Qn = !1;
	function $n(e, t) {
		switch (e) {
			case "keyup": return Kn.indexOf(t.keyCode) !== -1;
			case "keydown": return t.keyCode !== 229;
			case "keypress":
			case "mousedown":
			case "focusout": return !0;
			default: return !1;
		}
	}
	function er(e) {
		return e = e.detail, typeof e == "object" && "data" in e ? e.data : null;
	}
	var tr = !1;
	function nr(e, t) {
		switch (e) {
			case "compositionend": return er(t);
			case "keypress": return t.which === 32 ? (Qn = !0, Zn) : null;
			case "textInput": return e = t.data, e === Zn && Qn ? null : e;
			default: return null;
		}
	}
	function rr(e, t) {
		if (tr) return e === "compositionend" || !qn && $n(e, t) ? (e = _n(), I = gn = hn = null, tr = !1, e) : null;
		switch (e) {
			case "paste": return null;
			case "keypress":
				if (!(t.ctrlKey || t.altKey || t.metaKey) || t.ctrlKey && t.altKey) {
					if (t.char && 1 < t.char.length) return t.char;
					if (t.which) return String.fromCharCode(t.which);
				}
				return null;
			case "compositionend": return Xn && t.locale !== "ko" ? null : t.data;
			default: return null;
		}
	}
	var ir = {
		color: !0,
		date: !0,
		datetime: !0,
		"datetime-local": !0,
		email: !0,
		month: !0,
		number: !0,
		password: !0,
		range: !0,
		search: !0,
		tel: !0,
		text: !0,
		time: !0,
		url: !0,
		week: !0
	};
	function ar(e) {
		var t = e && e.nodeName && e.nodeName.toLowerCase();
		return t === "input" ? !!ir[e.type] : t === "textarea";
	}
	function or(e, t, n, r) {
		on ? sn ? sn.push(r) : sn = [r] : on = r, t = Ed(t, "onChange"), 0 < t.length && (n = new Sn("onChange", "change", null, n, r), e.push({
			event: n,
			listeners: t
		}));
	}
	var sr = null, cr = null;
	function lr(e) {
		yd(e, 0);
	}
	function ur(e) {
		if (zt(St(e))) return e;
	}
	function dr(e, t) {
		if (e === "change") return t;
	}
	var fr = !1;
	if (fn) {
		var pr;
		if (fn) {
			var mr = "oninput" in document;
			if (!mr) {
				var hr = document.createElement("div");
				hr.setAttribute("oninput", "return;"), mr = typeof hr.oninput == "function";
			}
			pr = mr;
		} else pr = !1;
		fr = pr && (!document.documentMode || 9 < document.documentMode);
	}
	function gr() {
		sr && (sr.detachEvent("onpropertychange", _r), cr = sr = null);
	}
	function _r(e) {
		if (e.propertyName === "value" && ur(cr)) {
			var t = [];
			or(t, cr, e, an(e)), un(lr, t);
		}
	}
	function vr(e, t, n) {
		e === "focusin" ? (gr(), sr = t, cr = n, sr.attachEvent("onpropertychange", _r)) : e === "focusout" && gr();
	}
	function yr(e) {
		if (e === "selectionchange" || e === "keyup" || e === "keydown") return ur(cr);
	}
	function br(e, t) {
		if (e === "click") return ur(t);
	}
	function xr(e, t) {
		if (e === "input" || e === "change") return ur(t);
	}
	function Sr(e, t) {
		return e === t && (e !== 0 || 1 / e == 1 / t) || e !== e && t !== t;
	}
	var Cr = typeof Object.is == "function" ? Object.is : Sr;
	function wr(e, t) {
		if (Cr(e, t)) return !0;
		if (typeof e != "object" || !e || typeof t != "object" || !t) return !1;
		var n = Object.keys(e), r = Object.keys(t);
		if (n.length !== r.length) return !1;
		for (r = 0; r < n.length; r++) {
			var i = n[r];
			if (!De.call(t, i) || !Cr(e[i], t[i])) return !1;
		}
		return !0;
	}
	function Tr(e) {
		for (; e && e.firstChild;) e = e.firstChild;
		return e;
	}
	function Er(e, t) {
		var n = Tr(e);
		e = 0;
		for (var r; n;) {
			if (n.nodeType === 3) {
				if (r = e + n.textContent.length, e <= t && r >= t) return {
					node: n,
					offset: t - e
				};
				e = r;
			}
			a: {
				for (; n;) {
					if (n.nextSibling) {
						n = n.nextSibling;
						break a;
					}
					n = n.parentNode;
				}
				n = void 0;
			}
			n = Tr(n);
		}
	}
	function Dr(e, t) {
		return e && t ? e === t ? !0 : e && e.nodeType === 3 ? !1 : t && t.nodeType === 3 ? Dr(e, t.parentNode) : "contains" in e ? e.contains(t) : e.compareDocumentPosition ? !!(e.compareDocumentPosition(t) & 16) : !1 : !1;
	}
	function Or(e) {
		e = e != null && e.ownerDocument != null && e.ownerDocument.defaultView != null ? e.ownerDocument.defaultView : window;
		for (var t = Bt(e.document); t instanceof e.HTMLIFrameElement;) {
			try {
				var n = typeof t.contentWindow.location.href == "string";
			} catch {
				n = !1;
			}
			if (n) e = t.contentWindow;
			else break;
			t = Bt(e.document);
		}
		return t;
	}
	function kr(e) {
		var t = e && e.nodeName && e.nodeName.toLowerCase();
		return t && (t === "input" && (e.type === "text" || e.type === "search" || e.type === "tel" || e.type === "url" || e.type === "password") || t === "textarea" || e.contentEditable === "true");
	}
	var Ar = fn && "documentMode" in document && 11 >= document.documentMode, jr = null, Mr = null, Nr = null, Pr = !1;
	function Fr(e, t, n) {
		var r = n.window === n ? n.document : n.nodeType === 9 ? n : n.ownerDocument;
		Pr || jr == null || jr !== Bt(r) || (r = jr, "selectionStart" in r && kr(r) ? r = {
			start: r.selectionStart,
			end: r.selectionEnd
		} : (r = (r.ownerDocument && r.ownerDocument.defaultView || window).getSelection(), r = {
			anchorNode: r.anchorNode,
			anchorOffset: r.anchorOffset,
			focusNode: r.focusNode,
			focusOffset: r.focusOffset
		}), Nr && wr(Nr, r) || (Nr = r, r = Ed(Mr, "onSelect"), 0 < r.length && (t = new Sn("onSelect", "select", null, t, n), e.push({
			event: t,
			listeners: r
		}), t.target = jr)));
	}
	function Ir(e, t) {
		var n = {};
		return n[e.toLowerCase()] = t.toLowerCase(), n["Webkit" + e] = "webkit" + t, n["Moz" + e] = "moz" + t, n;
	}
	var Lr = {
		animationend: Ir("Animation", "AnimationEnd"),
		animationiteration: Ir("Animation", "AnimationIteration"),
		animationstart: Ir("Animation", "AnimationStart"),
		transitionrun: Ir("Transition", "TransitionRun"),
		transitionstart: Ir("Transition", "TransitionStart"),
		transitioncancel: Ir("Transition", "TransitionCancel"),
		transitionend: Ir("Transition", "TransitionEnd")
	}, Rr = {}, zr = {};
	fn && (zr = document.createElement("div").style, "AnimationEvent" in window || (delete Lr.animationend.animation, delete Lr.animationiteration.animation, delete Lr.animationstart.animation), "TransitionEvent" in window || delete Lr.transitionend.transition);
	function Br(e) {
		if (Rr[e]) return Rr[e];
		if (!Lr[e]) return e;
		var t = Lr[e], n;
		for (n in t) if (t.hasOwnProperty(n) && n in zr) return Rr[e] = t[n];
		return e;
	}
	var Vr = Br("animationend"), Hr = Br("animationiteration"), Ur = Br("animationstart"), Wr = Br("transitionrun"), Gr = Br("transitionstart"), Kr = Br("transitioncancel"), qr = Br("transitionend"), Jr = /* @__PURE__ */ new Map(), Yr = "abort auxClick beforeToggle cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel".split(" ");
	Yr.push("scrollEnd");
	function Xr(e, t) {
		Jr.set(e, t), Et(t, [e]);
	}
	var Zr = typeof reportError == "function" ? reportError : function(e) {
		if (typeof window == "object" && typeof window.ErrorEvent == "function") {
			var t = new window.ErrorEvent("error", {
				bubbles: !0,
				cancelable: !0,
				message: typeof e == "object" && e && typeof e.message == "string" ? String(e.message) : String(e),
				error: e
			});
			if (!window.dispatchEvent(t)) return;
		} else if (typeof process == "object" && typeof process.emit == "function") {
			process.emit("uncaughtException", e);
			return;
		}
		console.error(e);
	}, Qr = [], $r = 0, ei = 0;
	function ti() {
		for (var e = $r, t = ei = $r = 0; t < e;) {
			var n = Qr[t];
			Qr[t++] = null;
			var r = Qr[t];
			Qr[t++] = null;
			var i = Qr[t];
			Qr[t++] = null;
			var a = Qr[t];
			if (Qr[t++] = null, r !== null && i !== null) {
				var o = r.pending;
				o === null ? i.next = i : (i.next = o.next, o.next = i), r.pending = i;
			}
			a !== 0 && ai(n, i, a);
		}
	}
	function ni(e, t, n, r) {
		Qr[$r++] = e, Qr[$r++] = t, Qr[$r++] = n, Qr[$r++] = r, ei |= r, e.lanes |= r, e = e.alternate, e !== null && (e.lanes |= r);
	}
	function ri(e, t, n, r) {
		return ni(e, t, n, r), oi(e);
	}
	function ii(e, t) {
		return ni(e, null, null, t), oi(e);
	}
	function ai(e, t, n) {
		e.lanes |= n;
		var r = e.alternate;
		r !== null && (r.lanes |= n);
		for (var i = !1, a = e.return; a !== null;) a.childLanes |= n, r = a.alternate, r !== null && (r.childLanes |= n), a.tag === 22 && (e = a.stateNode, e === null || e._visibility & 1 || (i = !0)), e = a, a = a.return;
		return e.tag === 3 ? (a = e.stateNode, i && t !== null && (i = 31 - Ue(n), e = a.hiddenUpdates, r = e[i], r === null ? e[i] = [t] : r.push(t), t.lane = n | 536870912), a) : null;
	}
	function oi(e) {
		if (50 < du) throw du = 0, fu = null, Error(a(185));
		for (var t = e.return; t !== null;) e = t, t = e.return;
		return e.tag === 3 ? e.stateNode : null;
	}
	var si = {};
	function ci(e, t, n, r) {
		this.tag = e, this.key = n, this.sibling = this.child = this.return = this.stateNode = this.type = this.elementType = null, this.index = 0, this.refCleanup = this.ref = null, this.pendingProps = t, this.dependencies = this.memoizedState = this.updateQueue = this.memoizedProps = null, this.mode = r, this.subtreeFlags = this.flags = 0, this.deletions = null, this.childLanes = this.lanes = 0, this.alternate = null;
	}
	function li(e, t, n, r) {
		return new ci(e, t, n, r);
	}
	function ui(e) {
		return e = e.prototype, !(!e || !e.isReactComponent);
	}
	function di(e, t) {
		var n = e.alternate;
		return n === null ? (n = li(e.tag, t, e.key, e.mode), n.elementType = e.elementType, n.type = e.type, n.stateNode = e.stateNode, n.alternate = e, e.alternate = n) : (n.pendingProps = t, n.type = e.type, n.flags = 0, n.subtreeFlags = 0, n.deletions = null), n.flags = e.flags & 65011712, n.childLanes = e.childLanes, n.lanes = e.lanes, n.child = e.child, n.memoizedProps = e.memoizedProps, n.memoizedState = e.memoizedState, n.updateQueue = e.updateQueue, t = e.dependencies, n.dependencies = t === null ? null : {
			lanes: t.lanes,
			firstContext: t.firstContext
		}, n.sibling = e.sibling, n.index = e.index, n.ref = e.ref, n.refCleanup = e.refCleanup, n;
	}
	function fi(e, t) {
		e.flags &= 65011714;
		var n = e.alternate;
		return n === null ? (e.childLanes = 0, e.lanes = t, e.child = null, e.subtreeFlags = 0, e.memoizedProps = null, e.memoizedState = null, e.updateQueue = null, e.dependencies = null, e.stateNode = null) : (e.childLanes = n.childLanes, e.lanes = n.lanes, e.child = n.child, e.subtreeFlags = 0, e.deletions = null, e.memoizedProps = n.memoizedProps, e.memoizedState = n.memoizedState, e.updateQueue = n.updateQueue, e.type = n.type, t = n.dependencies, e.dependencies = t === null ? null : {
			lanes: t.lanes,
			firstContext: t.firstContext
		}), e;
	}
	function pi(e, t, n, r, i, o) {
		var s = 0;
		if (r = e, typeof e == "function") ui(e) && (s = 1);
		else if (typeof e == "string") s = Uf(e, n, fe.current) ? 26 : e === "html" || e === "head" || e === "body" ? 27 : 5;
		else a: switch (e) {
			case ne: return e = li(31, n, t, i), e.elementType = ne, e.lanes = o, e;
			case y: return mi(n.children, i, o, t);
			case b:
				s = 8, i |= 24;
				break;
			case x: return e = li(12, n, t, i | 2), e.elementType = x, e.lanes = o, e;
			case T: return e = li(13, n, t, i), e.elementType = T, e.lanes = o, e;
			case ee: return e = li(19, n, t, i), e.elementType = ee, e.lanes = o, e;
			default:
				if (typeof e == "object" && e) switch (e.$$typeof) {
					case C:
						s = 10;
						break a;
					case S:
						s = 9;
						break a;
					case w:
						s = 11;
						break a;
					case te:
						s = 14;
						break a;
					case E:
						s = 16, r = null;
						break a;
				}
				s = 29, n = Error(a(130, e === null ? "null" : typeof e, "")), r = null;
		}
		return t = li(s, n, t, i), t.elementType = e, t.type = r, t.lanes = o, t;
	}
	function mi(e, t, n, r) {
		return e = li(7, e, r, t), e.lanes = n, e;
	}
	function hi(e, t, n) {
		return e = li(6, e, null, t), e.lanes = n, e;
	}
	function gi(e) {
		var t = li(18, null, null, 0);
		return t.stateNode = e, t;
	}
	function _i(e, t, n) {
		return t = li(4, e.children === null ? [] : e.children, e.key, t), t.lanes = n, t.stateNode = {
			containerInfo: e.containerInfo,
			pendingChildren: null,
			implementation: e.implementation
		}, t;
	}
	var vi = /* @__PURE__ */ new WeakMap();
	function yi(e, t) {
		if (typeof e == "object" && e) {
			var n = vi.get(e);
			return n === void 0 ? (t = {
				value: e,
				source: t,
				stack: Ee(t)
			}, vi.set(e, t), t) : n;
		}
		return {
			value: e,
			source: t,
			stack: Ee(t)
		};
	}
	var bi = [], xi = 0, Si = null, Ci = 0, wi = [], Ti = 0, Ei = null, Di = 1, Oi = "";
	function ki(e, t) {
		bi[xi++] = Ci, bi[xi++] = Si, Si = e, Ci = t;
	}
	function Ai(e, t, n) {
		wi[Ti++] = Di, wi[Ti++] = Oi, wi[Ti++] = Ei, Ei = e;
		var r = Di;
		e = Oi;
		var i = 32 - Ue(r) - 1;
		r &= ~(1 << i), n += 1;
		var a = 32 - Ue(t) + i;
		if (30 < a) {
			var o = i - i % 5;
			a = (r & (1 << o) - 1).toString(32), r >>= o, i -= o, Di = 1 << 32 - Ue(t) + i | n << i | r, Oi = a + e;
		} else Di = 1 << a | n << i | r, Oi = e;
	}
	function ji(e) {
		e.return !== null && (ki(e, 1), Ai(e, 1, 0));
	}
	function Mi(e) {
		for (; e === Si;) Si = bi[--xi], bi[xi] = null, Ci = bi[--xi], bi[xi] = null;
		for (; e === Ei;) Ei = wi[--Ti], wi[Ti] = null, Oi = wi[--Ti], wi[Ti] = null, Di = wi[--Ti], wi[Ti] = null;
	}
	function Ni(e, t) {
		wi[Ti++] = Di, wi[Ti++] = Oi, wi[Ti++] = Ei, Di = t.id, Oi = t.overflow, Ei = e;
	}
	var Pi = null, R = null, z = !1, Fi = null, Ii = !1, Li = Error(a(519));
	function Ri(e) {
		throw Wi(yi(Error(a(418, 1 < arguments.length && arguments[1] !== void 0 && arguments[1] ? "text" : "HTML", "")), e)), Li;
	}
	function zi(e) {
		var t = e.stateNode, n = e.type, r = e.memoizedProps;
		switch (t[ft] = e, t[pt] = r, n) {
			case "dialog":
				Q("cancel", t), Q("close", t);
				break;
			case "iframe":
			case "object":
			case "embed":
				Q("load", t);
				break;
			case "video":
			case "audio":
				for (n = 0; n < _d.length; n++) Q(_d[n], t);
				break;
			case "source":
				Q("error", t);
				break;
			case "img":
			case "image":
			case "link":
				Q("error", t), Q("load", t);
				break;
			case "details":
				Q("toggle", t);
				break;
			case "input":
				Q("invalid", t), Wt(t, r.value, r.defaultValue, r.checked, r.defaultChecked, r.type, r.name, !0);
				break;
			case "select":
				Q("invalid", t);
				break;
			case "textarea": Q("invalid", t), Jt(t, r.value, r.defaultValue, r.children);
		}
		n = r.children, typeof n != "string" && typeof n != "number" && typeof n != "bigint" || t.textContent === "" + n || !0 === r.suppressHydrationWarning || Md(t.textContent, n) ? (r.popover != null && (Q("beforetoggle", t), Q("toggle", t)), r.onScroll != null && Q("scroll", t), r.onScrollEnd != null && Q("scrollend", t), r.onClick != null && (t.onclick = F), t = !0) : t = !1, t || Ri(e, !0);
	}
	function Bi(e) {
		for (Pi = e.return; Pi;) switch (Pi.tag) {
			case 5:
			case 31:
			case 13:
				Ii = !1;
				return;
			case 27:
			case 3:
				Ii = !0;
				return;
			default: Pi = Pi.return;
		}
	}
	function Vi(e) {
		if (e !== Pi) return !1;
		if (!z) return Bi(e), z = !0, !1;
		var t = e.tag, n;
		if ((n = t !== 3 && t !== 27) && ((n = t === 5) && (n = e.type, n = !(n !== "form" && n !== "button") || Ud(e.type, e.memoizedProps)), n = !n), n && R && Ri(e), Bi(e), t === 13) {
			if (e = e.memoizedState, e = e === null ? null : e.dehydrated, !e) throw Error(a(317));
			R = uf(e);
		} else if (t === 31) {
			if (e = e.memoizedState, e = e === null ? null : e.dehydrated, !e) throw Error(a(317));
			R = uf(e);
		} else t === 27 ? (t = R, Zd(e.type) ? (e = lf, lf = null, R = e) : R = t) : R = Pi ? cf(e.stateNode.nextSibling) : null;
		return !0;
	}
	function Hi() {
		R = Pi = null, z = !1;
	}
	function Ui() {
		var e = Fi;
		return e !== null && (Zl === null ? Zl = e : Zl.push.apply(Zl, e), Fi = null), e;
	}
	function Wi(e) {
		Fi === null ? Fi = [e] : Fi.push(e);
	}
	var Gi = de(null), Ki = null, qi = null;
	function Ji(e, t, n) {
		j(Gi, t._currentValue), t._currentValue = n;
	}
	function Yi(e) {
		e._currentValue = Gi.current, A(Gi);
	}
	function Xi(e, t, n) {
		for (; e !== null;) {
			var r = e.alternate;
			if ((e.childLanes & t) === t ? r !== null && (r.childLanes & t) !== t && (r.childLanes |= t) : (e.childLanes |= t, r !== null && (r.childLanes |= t)), e === n) break;
			e = e.return;
		}
	}
	function Zi(e, t, n, r) {
		var i = e.child;
		for (i !== null && (i.return = e); i !== null;) {
			var o = i.dependencies;
			if (o !== null) {
				var s = i.child;
				o = o.firstContext;
				a: for (; o !== null;) {
					var c = o;
					o = i;
					for (var l = 0; l < t.length; l++) if (c.context === t[l]) {
						o.lanes |= n, c = o.alternate, c !== null && (c.lanes |= n), Xi(o.return, n, e), r || (s = null);
						break a;
					}
					o = c.next;
				}
			} else if (i.tag === 18) {
				if (s = i.return, s === null) throw Error(a(341));
				s.lanes |= n, o = s.alternate, o !== null && (o.lanes |= n), Xi(s, n, e), s = null;
			} else s = i.child;
			if (s !== null) s.return = i;
			else for (s = i; s !== null;) {
				if (s === e) {
					s = null;
					break;
				}
				if (i = s.sibling, i !== null) {
					i.return = s.return, s = i;
					break;
				}
				s = s.return;
			}
			i = s;
		}
	}
	function Qi(e, t, n, r) {
		e = null;
		for (var i = t, o = !1; i !== null;) {
			if (!o) {
				if (i.flags & 524288) o = !0;
				else if (i.flags & 262144) break;
			}
			if (i.tag === 10) {
				var s = i.alternate;
				if (s === null) throw Error(a(387));
				if (s = s.memoizedProps, s !== null) {
					var c = i.type;
					Cr(i.pendingProps.value, s.value) || (e === null ? e = [c] : e.push(c));
				}
			} else if (i === he.current) {
				if (s = i.alternate, s === null) throw Error(a(387));
				s.memoizedState.memoizedState !== i.memoizedState.memoizedState && (e === null ? e = [Qf] : e.push(Qf));
			}
			i = i.return;
		}
		e !== null && Zi(t, e, n, r), t.flags |= 262144;
	}
	function $i(e) {
		for (e = e.firstContext; e !== null;) {
			if (!Cr(e.context._currentValue, e.memoizedValue)) return !0;
			e = e.next;
		}
		return !1;
	}
	function ea(e) {
		Ki = e, qi = null, e = e.dependencies, e !== null && (e.firstContext = null);
	}
	function ta(e) {
		return ra(Ki, e);
	}
	function na(e, t) {
		return Ki === null && ea(e), ra(e, t);
	}
	function ra(e, t) {
		var n = t._currentValue;
		if (t = {
			context: t,
			memoizedValue: n,
			next: null
		}, qi === null) {
			if (e === null) throw Error(a(308));
			qi = t, e.dependencies = {
				lanes: 0,
				firstContext: t
			}, e.flags |= 524288;
		} else qi = qi.next = t;
		return n;
	}
	var ia = typeof AbortController < "u" ? AbortController : function() {
		var e = [], t = this.signal = {
			aborted: !1,
			addEventListener: function(t, n) {
				e.push(n);
			}
		};
		this.abort = function() {
			t.aborted = !0, e.forEach(function(e) {
				return e();
			});
		};
	}, aa = t.unstable_scheduleCallback, oa = t.unstable_NormalPriority, sa = {
		$$typeof: C,
		Consumer: null,
		Provider: null,
		_currentValue: null,
		_currentValue2: null,
		_threadCount: 0
	};
	function ca() {
		return {
			controller: new ia(),
			data: /* @__PURE__ */ new Map(),
			refCount: 0
		};
	}
	function la(e) {
		e.refCount--, e.refCount === 0 && aa(oa, function() {
			e.controller.abort();
		});
	}
	var ua = null, da = 0, fa = 0, pa = null;
	function ma(e, t) {
		if (ua === null) {
			var n = ua = [];
			da = 0, fa = dd(), pa = {
				status: "pending",
				value: void 0,
				then: function(e) {
					n.push(e);
				}
			};
		}
		return da++, t.then(ha, ha), t;
	}
	function ha() {
		if (--da === 0 && ua !== null) {
			pa !== null && (pa.status = "fulfilled");
			var e = ua;
			ua = null, fa = 0, pa = null;
			for (var t = 0; t < e.length; t++) (0, e[t])();
		}
	}
	function ga(e, t) {
		var n = [], r = {
			status: "pending",
			value: null,
			reason: null,
			then: function(e) {
				n.push(e);
			}
		};
		return e.then(function() {
			r.status = "fulfilled", r.value = t;
			for (var e = 0; e < n.length; e++) (0, n[e])(t);
		}, function(e) {
			for (r.status = "rejected", r.reason = e, e = 0; e < n.length; e++) (0, n[e])(void 0);
		}), r;
	}
	var _a = O.S;
	O.S = function(e, t) {
		eu = je(), typeof t == "object" && t && typeof t.then == "function" && ma(e, t), _a !== null && _a(e, t);
	};
	var va = de(null);
	function ya() {
		var e = va.current;
		return e === null ? K.pooledCache : e;
	}
	function ba(e, t) {
		t === null ? j(va, va.current) : j(va, t.pool);
	}
	function xa() {
		var e = ya();
		return e === null ? null : {
			parent: sa._currentValue,
			pool: e
		};
	}
	var Sa = Error(a(460)), Ca = Error(a(474)), wa = Error(a(542)), Ta = { then: function() {} };
	function Ea(e) {
		return e = e.status, e === "fulfilled" || e === "rejected";
	}
	function Da(e, t, n) {
		switch (n = e[n], n === void 0 ? e.push(t) : n !== t && (t.then(F, F), t = n), t.status) {
			case "fulfilled": return t.value;
			case "rejected": throw e = t.reason, ja(e), e;
			default:
				if (typeof t.status == "string") t.then(F, F);
				else {
					if (e = K, e !== null && 100 < e.shellSuspendCounter) throw Error(a(482));
					e = t, e.status = "pending", e.then(function(e) {
						if (t.status === "pending") {
							var n = t;
							n.status = "fulfilled", n.value = e;
						}
					}, function(e) {
						if (t.status === "pending") {
							var n = t;
							n.status = "rejected", n.reason = e;
						}
					});
				}
				switch (t.status) {
					case "fulfilled": return t.value;
					case "rejected": throw e = t.reason, ja(e), e;
				}
				throw ka = t, Sa;
		}
	}
	function Oa(e) {
		try {
			var t = e._init;
			return t(e._payload);
		} catch (e) {
			throw typeof e == "object" && e && typeof e.then == "function" ? (ka = e, Sa) : e;
		}
	}
	var ka = null;
	function Aa() {
		if (ka === null) throw Error(a(459));
		var e = ka;
		return ka = null, e;
	}
	function ja(e) {
		if (e === Sa || e === wa) throw Error(a(483));
	}
	var Ma = null, Na = 0;
	function Pa(e) {
		var t = Na;
		return Na += 1, Ma === null && (Ma = []), Da(Ma, e, t);
	}
	function Fa(e, t) {
		t = t.props.ref, e.ref = t === void 0 ? null : t;
	}
	function Ia(e, t) {
		throw t.$$typeof === g ? Error(a(525)) : (e = Object.prototype.toString.call(t), Error(a(31, e === "[object Object]" ? "object with keys {" + Object.keys(t).join(", ") + "}" : e)));
	}
	function La(e) {
		function t(t, n) {
			if (e) {
				var r = t.deletions;
				r === null ? (t.deletions = [n], t.flags |= 16) : r.push(n);
			}
		}
		function n(n, r) {
			if (!e) return null;
			for (; r !== null;) t(n, r), r = r.sibling;
			return null;
		}
		function r(e) {
			for (var t = /* @__PURE__ */ new Map(); e !== null;) e.key === null ? t.set(e.index, e) : t.set(e.key, e), e = e.sibling;
			return t;
		}
		function i(e, t) {
			return e = di(e, t), e.index = 0, e.sibling = null, e;
		}
		function o(t, n, r) {
			return t.index = r, e ? (r = t.alternate, r === null ? (t.flags |= 67108866, n) : (r = r.index, r < n ? (t.flags |= 67108866, n) : r)) : (t.flags |= 1048576, n);
		}
		function s(t) {
			return e && t.alternate === null && (t.flags |= 67108866), t;
		}
		function c(e, t, n, r) {
			return t === null || t.tag !== 6 ? (t = hi(n, e.mode, r), t.return = e, t) : (t = i(t, n), t.return = e, t);
		}
		function l(e, t, n, r) {
			var a = n.type;
			return a === y ? d(e, t, n.props.children, r, n.key) : t !== null && (t.elementType === a || typeof a == "object" && a && a.$$typeof === E && Oa(a) === t.type) ? (t = i(t, n.props), Fa(t, n), t.return = e, t) : (t = pi(n.type, n.key, n.props, null, e.mode, r), Fa(t, n), t.return = e, t);
		}
		function u(e, t, n, r) {
			return t === null || t.tag !== 4 || t.stateNode.containerInfo !== n.containerInfo || t.stateNode.implementation !== n.implementation ? (t = _i(n, e.mode, r), t.return = e, t) : (t = i(t, n.children || []), t.return = e, t);
		}
		function d(e, t, n, r, a) {
			return t === null || t.tag !== 7 ? (t = mi(n, e.mode, r, a), t.return = e, t) : (t = i(t, n), t.return = e, t);
		}
		function f(e, t, n) {
			if (typeof t == "string" && t !== "" || typeof t == "number" || typeof t == "bigint") return t = hi("" + t, e.mode, n), t.return = e, t;
			if (typeof t == "object" && t) {
				switch (t.$$typeof) {
					case _: return n = pi(t.type, t.key, t.props, null, e.mode, n), Fa(n, t), n.return = e, n;
					case v: return t = _i(t, e.mode, n), t.return = e, t;
					case E: return t = Oa(t), f(e, t, n);
				}
				if (se(t) || ae(t)) return t = mi(t, e.mode, n, null), t.return = e, t;
				if (typeof t.then == "function") return f(e, Pa(t), n);
				if (t.$$typeof === C) return f(e, na(e, t), n);
				Ia(e, t);
			}
			return null;
		}
		function p(e, t, n, r) {
			var i = t === null ? null : t.key;
			if (typeof n == "string" && n !== "" || typeof n == "number" || typeof n == "bigint") return i === null ? c(e, t, "" + n, r) : null;
			if (typeof n == "object" && n) {
				switch (n.$$typeof) {
					case _: return n.key === i ? l(e, t, n, r) : null;
					case v: return n.key === i ? u(e, t, n, r) : null;
					case E: return n = Oa(n), p(e, t, n, r);
				}
				if (se(n) || ae(n)) return i === null ? d(e, t, n, r, null) : null;
				if (typeof n.then == "function") return p(e, t, Pa(n), r);
				if (n.$$typeof === C) return p(e, t, na(e, n), r);
				Ia(e, n);
			}
			return null;
		}
		function m(e, t, n, r, i) {
			if (typeof r == "string" && r !== "" || typeof r == "number" || typeof r == "bigint") return e = e.get(n) || null, c(t, e, "" + r, i);
			if (typeof r == "object" && r) {
				switch (r.$$typeof) {
					case _: return e = e.get(r.key === null ? n : r.key) || null, l(t, e, r, i);
					case v: return e = e.get(r.key === null ? n : r.key) || null, u(t, e, r, i);
					case E: return r = Oa(r), m(e, t, n, r, i);
				}
				if (se(r) || ae(r)) return e = e.get(n) || null, d(t, e, r, i, null);
				if (typeof r.then == "function") return m(e, t, n, Pa(r), i);
				if (r.$$typeof === C) return m(e, t, n, na(t, r), i);
				Ia(t, r);
			}
			return null;
		}
		function h(i, a, s, c) {
			for (var l = null, u = null, d = a, h = a = 0, g = null; d !== null && h < s.length; h++) {
				d.index > h ? (g = d, d = null) : g = d.sibling;
				var _ = p(i, d, s[h], c);
				if (_ === null) {
					d === null && (d = g);
					break;
				}
				e && d && _.alternate === null && t(i, d), a = o(_, a, h), u === null ? l = _ : u.sibling = _, u = _, d = g;
			}
			if (h === s.length) return n(i, d), z && ki(i, h), l;
			if (d === null) {
				for (; h < s.length; h++) d = f(i, s[h], c), d !== null && (a = o(d, a, h), u === null ? l = d : u.sibling = d, u = d);
				return z && ki(i, h), l;
			}
			for (d = r(d); h < s.length; h++) g = m(d, i, h, s[h], c), g !== null && (e && g.alternate !== null && d.delete(g.key === null ? h : g.key), a = o(g, a, h), u === null ? l = g : u.sibling = g, u = g);
			return e && d.forEach(function(e) {
				return t(i, e);
			}), z && ki(i, h), l;
		}
		function g(i, s, c, l) {
			if (c == null) throw Error(a(151));
			for (var u = null, d = null, h = s, g = s = 0, _ = null, v = c.next(); h !== null && !v.done; g++, v = c.next()) {
				h.index > g ? (_ = h, h = null) : _ = h.sibling;
				var y = p(i, h, v.value, l);
				if (y === null) {
					h === null && (h = _);
					break;
				}
				e && h && y.alternate === null && t(i, h), s = o(y, s, g), d === null ? u = y : d.sibling = y, d = y, h = _;
			}
			if (v.done) return n(i, h), z && ki(i, g), u;
			if (h === null) {
				for (; !v.done; g++, v = c.next()) v = f(i, v.value, l), v !== null && (s = o(v, s, g), d === null ? u = v : d.sibling = v, d = v);
				return z && ki(i, g), u;
			}
			for (h = r(h); !v.done; g++, v = c.next()) v = m(h, i, g, v.value, l), v !== null && (e && v.alternate !== null && h.delete(v.key === null ? g : v.key), s = o(v, s, g), d === null ? u = v : d.sibling = v, d = v);
			return e && h.forEach(function(e) {
				return t(i, e);
			}), z && ki(i, g), u;
		}
		function b(e, r, o, c) {
			if (typeof o == "object" && o && o.type === y && o.key === null && (o = o.props.children), typeof o == "object" && o) {
				switch (o.$$typeof) {
					case _:
						a: {
							for (var l = o.key; r !== null;) {
								if (r.key === l) {
									if (l = o.type, l === y) {
										if (r.tag === 7) {
											n(e, r.sibling), c = i(r, o.props.children), c.return = e, e = c;
											break a;
										}
									} else if (r.elementType === l || typeof l == "object" && l && l.$$typeof === E && Oa(l) === r.type) {
										n(e, r.sibling), c = i(r, o.props), Fa(c, o), c.return = e, e = c;
										break a;
									}
									n(e, r);
									break;
								} else t(e, r);
								r = r.sibling;
							}
							o.type === y ? (c = mi(o.props.children, e.mode, c, o.key), c.return = e, e = c) : (c = pi(o.type, o.key, o.props, null, e.mode, c), Fa(c, o), c.return = e, e = c);
						}
						return s(e);
					case v:
						a: {
							for (l = o.key; r !== null;) {
								if (r.key === l) if (r.tag === 4 && r.stateNode.containerInfo === o.containerInfo && r.stateNode.implementation === o.implementation) {
									n(e, r.sibling), c = i(r, o.children || []), c.return = e, e = c;
									break a;
								} else {
									n(e, r);
									break;
								}
								else t(e, r);
								r = r.sibling;
							}
							c = _i(o, e.mode, c), c.return = e, e = c;
						}
						return s(e);
					case E: return o = Oa(o), b(e, r, o, c);
				}
				if (se(o)) return h(e, r, o, c);
				if (ae(o)) {
					if (l = ae(o), typeof l != "function") throw Error(a(150));
					return o = l.call(o), g(e, r, o, c);
				}
				if (typeof o.then == "function") return b(e, r, Pa(o), c);
				if (o.$$typeof === C) return b(e, r, na(e, o), c);
				Ia(e, o);
			}
			return typeof o == "string" && o !== "" || typeof o == "number" || typeof o == "bigint" ? (o = "" + o, r !== null && r.tag === 6 ? (n(e, r.sibling), c = i(r, o), c.return = e, e = c) : (n(e, r), c = hi(o, e.mode, c), c.return = e, e = c), s(e)) : n(e, r);
		}
		return function(e, t, n, r) {
			try {
				Na = 0;
				var i = b(e, t, n, r);
				return Ma = null, i;
			} catch (t) {
				if (t === Sa || t === wa) throw t;
				var a = li(29, t, null, e.mode);
				return a.lanes = r, a.return = e, a;
			}
		};
	}
	var Ra = La(!0), za = La(!1), Ba = !1;
	function Va(e) {
		e.updateQueue = {
			baseState: e.memoizedState,
			firstBaseUpdate: null,
			lastBaseUpdate: null,
			shared: {
				pending: null,
				lanes: 0,
				hiddenCallbacks: null
			},
			callbacks: null
		};
	}
	function Ha(e, t) {
		e = e.updateQueue, t.updateQueue === e && (t.updateQueue = {
			baseState: e.baseState,
			firstBaseUpdate: e.firstBaseUpdate,
			lastBaseUpdate: e.lastBaseUpdate,
			shared: e.shared,
			callbacks: null
		});
	}
	function Ua(e) {
		return {
			lane: e,
			tag: 0,
			payload: null,
			callback: null,
			next: null
		};
	}
	function Wa(e, t, n) {
		var r = e.updateQueue;
		if (r === null) return null;
		if (r = r.shared, G & 2) {
			var i = r.pending;
			return i === null ? t.next = t : (t.next = i.next, i.next = t), r.pending = t, t = oi(e), ai(e, null, n), t;
		}
		return ni(e, r, t, n), oi(e);
	}
	function Ga(e, t, n) {
		if (t = t.updateQueue, t !== null && (t = t.shared, n & 4194048)) {
			var r = t.lanes;
			r &= e.pendingLanes, n |= r, t.lanes = n, at(e, n);
		}
	}
	function Ka(e, t) {
		var n = e.updateQueue, r = e.alternate;
		if (r !== null && (r = r.updateQueue, n === r)) {
			var i = null, a = null;
			if (n = n.firstBaseUpdate, n !== null) {
				do {
					var o = {
						lane: n.lane,
						tag: n.tag,
						payload: n.payload,
						callback: null,
						next: null
					};
					a === null ? i = a = o : a = a.next = o, n = n.next;
				} while (n !== null);
				a === null ? i = a = t : a = a.next = t;
			} else i = a = t;
			n = {
				baseState: r.baseState,
				firstBaseUpdate: i,
				lastBaseUpdate: a,
				shared: r.shared,
				callbacks: r.callbacks
			}, e.updateQueue = n;
			return;
		}
		e = n.lastBaseUpdate, e === null ? n.firstBaseUpdate = t : e.next = t, n.lastBaseUpdate = t;
	}
	var qa = !1;
	function Ja() {
		if (qa) {
			var e = pa;
			if (e !== null) throw e;
		}
	}
	function Ya(e, t, n, r) {
		qa = !1;
		var i = e.updateQueue;
		Ba = !1;
		var a = i.firstBaseUpdate, o = i.lastBaseUpdate, s = i.shared.pending;
		if (s !== null) {
			i.shared.pending = null;
			var c = s, l = c.next;
			c.next = null, o === null ? a = l : o.next = l, o = c;
			var u = e.alternate;
			u !== null && (u = u.updateQueue, s = u.lastBaseUpdate, s !== o && (s === null ? u.firstBaseUpdate = l : s.next = l, u.lastBaseUpdate = c));
		}
		if (a !== null) {
			var d = i.baseState;
			o = 0, u = l = c = null, s = a;
			do {
				var f = s.lane & -536870913, p = f !== s.lane;
				if (p ? (J & f) === f : (r & f) === f) {
					f !== 0 && f === fa && (qa = !0), u !== null && (u = u.next = {
						lane: 0,
						tag: s.tag,
						payload: s.payload,
						callback: null,
						next: null
					});
					a: {
						var m = e, g = s;
						f = t;
						var _ = n;
						switch (g.tag) {
							case 1:
								if (m = g.payload, typeof m == "function") {
									d = m.call(_, d, f);
									break a;
								}
								d = m;
								break a;
							case 3: m.flags = m.flags & -65537 | 128;
							case 0:
								if (m = g.payload, f = typeof m == "function" ? m.call(_, d, f) : m, f == null) break a;
								d = h({}, d, f);
								break a;
							case 2: Ba = !0;
						}
					}
					f = s.callback, f !== null && (e.flags |= 64, p && (e.flags |= 8192), p = i.callbacks, p === null ? i.callbacks = [f] : p.push(f));
				} else p = {
					lane: f,
					tag: s.tag,
					payload: s.payload,
					callback: s.callback,
					next: null
				}, u === null ? (l = u = p, c = d) : u = u.next = p, o |= f;
				if (s = s.next, s === null) {
					if (s = i.shared.pending, s === null) break;
					p = s, s = p.next, p.next = null, i.lastBaseUpdate = p, i.shared.pending = null;
				}
			} while (1);
			u === null && (c = d), i.baseState = c, i.firstBaseUpdate = l, i.lastBaseUpdate = u, a === null && (i.shared.lanes = 0), Gl |= o, e.lanes = o, e.memoizedState = d;
		}
	}
	function Xa(e, t) {
		if (typeof e != "function") throw Error(a(191, e));
		e.call(t);
	}
	function Za(e, t) {
		var n = e.callbacks;
		if (n !== null) for (e.callbacks = null, e = 0; e < n.length; e++) Xa(n[e], t);
	}
	var Qa = de(null), $a = de(0);
	function eo(e, t) {
		e = Wl, j($a, e), j(Qa, t), Wl = e | t.baseLanes;
	}
	function to() {
		j($a, Wl), j(Qa, Qa.current);
	}
	function no() {
		Wl = $a.current, A(Qa), A($a);
	}
	var ro = de(null), io = null;
	function ao(e) {
		var t = e.alternate;
		j(uo, uo.current & 1), j(ro, e), io === null && (t === null || Qa.current !== null || t.memoizedState !== null) && (io = e);
	}
	function oo(e) {
		j(uo, uo.current), j(ro, e), io === null && (io = e);
	}
	function so(e) {
		e.tag === 22 ? (j(uo, uo.current), j(ro, e), io === null && (io = e)) : co(e);
	}
	function co() {
		j(uo, uo.current), j(ro, ro.current);
	}
	function lo(e) {
		A(ro), io === e && (io = null), A(uo);
	}
	var uo = de(0);
	function fo(e) {
		for (var t = e; t !== null;) {
			if (t.tag === 13) {
				var n = t.memoizedState;
				if (n !== null && (n = n.dehydrated, n === null || af(n) || of(n))) return t;
			} else if (t.tag === 19 && (t.memoizedProps.revealOrder === "forwards" || t.memoizedProps.revealOrder === "backwards" || t.memoizedProps.revealOrder === "unstable_legacy-backwards" || t.memoizedProps.revealOrder === "together")) {
				if (t.flags & 128) return t;
			} else if (t.child !== null) {
				t.child.return = t, t = t.child;
				continue;
			}
			if (t === e) break;
			for (; t.sibling === null;) {
				if (t.return === null || t.return === e) return null;
				t = t.return;
			}
			t.sibling.return = t.return, t = t.sibling;
		}
		return null;
	}
	var po = 0, B = null, V = null, mo = null, ho = !1, go = !1, _o = !1, vo = 0, yo = 0, bo = null, xo = 0;
	function H() {
		throw Error(a(321));
	}
	function So(e, t) {
		if (t === null) return !1;
		for (var n = 0; n < t.length && n < e.length; n++) if (!Cr(e[n], t[n])) return !1;
		return !0;
	}
	function Co(e, t, n, r, i, a) {
		return po = a, B = t, t.memoizedState = null, t.updateQueue = null, t.lanes = 0, O.H = e === null || e.memoizedState === null ? Bs : Vs, _o = !1, a = n(r, i), _o = !1, go && (a = To(t, n, r, i)), wo(e), a;
	}
	function wo(e) {
		O.H = zs;
		var t = V !== null && V.next !== null;
		if (po = 0, mo = V = B = null, ho = !1, yo = 0, bo = null, t) throw Error(a(300));
		e === null || ic || (e = e.dependencies, e !== null && $i(e) && (ic = !0));
	}
	function To(e, t, n, r) {
		B = e;
		var i = 0;
		do {
			if (go && (bo = null), yo = 0, go = !1, 25 <= i) throw Error(a(301));
			if (i += 1, mo = V = null, e.updateQueue != null) {
				var o = e.updateQueue;
				o.lastEffect = null, o.events = null, o.stores = null, o.memoCache != null && (o.memoCache.index = 0);
			}
			O.H = Hs, o = t(n, r);
		} while (go);
		return o;
	}
	function Eo() {
		var e = O.H, t = e.useState()[0];
		return t = typeof t.then == "function" ? No(t) : t, e = e.useState()[0], (V === null ? null : V.memoizedState) !== e && (B.flags |= 1024), t;
	}
	function Do() {
		var e = vo !== 0;
		return vo = 0, e;
	}
	function Oo(e, t, n) {
		t.updateQueue = e.updateQueue, t.flags &= -2053, e.lanes &= ~n;
	}
	function ko(e) {
		if (ho) {
			for (e = e.memoizedState; e !== null;) {
				var t = e.queue;
				t !== null && (t.pending = null), e = e.next;
			}
			ho = !1;
		}
		po = 0, mo = V = B = null, go = !1, yo = vo = 0, bo = null;
	}
	function Ao() {
		var e = {
			memoizedState: null,
			baseState: null,
			baseQueue: null,
			queue: null,
			next: null
		};
		return mo === null ? B.memoizedState = mo = e : mo = mo.next = e, mo;
	}
	function jo() {
		if (V === null) {
			var e = B.alternate;
			e = e === null ? null : e.memoizedState;
		} else e = V.next;
		var t = mo === null ? B.memoizedState : mo.next;
		if (t !== null) mo = t, V = e;
		else {
			if (e === null) throw B.alternate === null ? Error(a(467)) : Error(a(310));
			V = e, e = {
				memoizedState: V.memoizedState,
				baseState: V.baseState,
				baseQueue: V.baseQueue,
				queue: V.queue,
				next: null
			}, mo === null ? B.memoizedState = mo = e : mo = mo.next = e;
		}
		return mo;
	}
	function Mo() {
		return {
			lastEffect: null,
			events: null,
			stores: null,
			memoCache: null
		};
	}
	function No(e) {
		var t = yo;
		return yo += 1, bo === null && (bo = []), e = Da(bo, e, t), t = B, (mo === null ? t.memoizedState : mo.next) === null && (t = t.alternate, O.H = t === null || t.memoizedState === null ? Bs : Vs), e;
	}
	function Po(e) {
		if (typeof e == "object" && e) {
			if (typeof e.then == "function") return No(e);
			if (e.$$typeof === C) return ta(e);
		}
		throw Error(a(438, String(e)));
	}
	function Fo(e) {
		var t = null, n = B.updateQueue;
		if (n !== null && (t = n.memoCache), t == null) {
			var r = B.alternate;
			r !== null && (r = r.updateQueue, r !== null && (r = r.memoCache, r != null && (t = {
				data: r.data.map(function(e) {
					return e.slice();
				}),
				index: 0
			})));
		}
		if (t ??= {
			data: [],
			index: 0
		}, n === null && (n = Mo(), B.updateQueue = n), n.memoCache = t, n = t.data[t.index], n === void 0) for (n = t.data[t.index] = Array(e), r = 0; r < e; r++) n[r] = re;
		return t.index++, n;
	}
	function Io(e, t) {
		return typeof t == "function" ? t(e) : t;
	}
	function Lo(e) {
		return Ro(jo(), V, e);
	}
	function Ro(e, t, n) {
		var r = e.queue;
		if (r === null) throw Error(a(311));
		r.lastRenderedReducer = n;
		var i = e.baseQueue, o = r.pending;
		if (o !== null) {
			if (i !== null) {
				var s = i.next;
				i.next = o.next, o.next = s;
			}
			t.baseQueue = i = o, r.pending = null;
		}
		if (o = e.baseState, i === null) e.memoizedState = o;
		else {
			t = i.next;
			var c = s = null, l = null, u = t, d = !1;
			do {
				var f = u.lane & -536870913;
				if (f === u.lane ? (po & f) === f : (J & f) === f) {
					var p = u.revertLane;
					if (p === 0) l !== null && (l = l.next = {
						lane: 0,
						revertLane: 0,
						gesture: null,
						action: u.action,
						hasEagerState: u.hasEagerState,
						eagerState: u.eagerState,
						next: null
					}), f === fa && (d = !0);
					else if ((po & p) === p) {
						u = u.next, p === fa && (d = !0);
						continue;
					} else f = {
						lane: 0,
						revertLane: u.revertLane,
						gesture: null,
						action: u.action,
						hasEagerState: u.hasEagerState,
						eagerState: u.eagerState,
						next: null
					}, l === null ? (c = l = f, s = o) : l = l.next = f, B.lanes |= p, Gl |= p;
					f = u.action, _o && n(o, f), o = u.hasEagerState ? u.eagerState : n(o, f);
				} else p = {
					lane: f,
					revertLane: u.revertLane,
					gesture: u.gesture,
					action: u.action,
					hasEagerState: u.hasEagerState,
					eagerState: u.eagerState,
					next: null
				}, l === null ? (c = l = p, s = o) : l = l.next = p, B.lanes |= f, Gl |= f;
				u = u.next;
			} while (u !== null && u !== t);
			if (l === null ? s = o : l.next = c, !Cr(o, e.memoizedState) && (ic = !0, d && (n = pa, n !== null))) throw n;
			e.memoizedState = o, e.baseState = s, e.baseQueue = l, r.lastRenderedState = o;
		}
		return i === null && (r.lanes = 0), [e.memoizedState, r.dispatch];
	}
	function zo(e) {
		var t = jo(), n = t.queue;
		if (n === null) throw Error(a(311));
		n.lastRenderedReducer = e;
		var r = n.dispatch, i = n.pending, o = t.memoizedState;
		if (i !== null) {
			n.pending = null;
			var s = i = i.next;
			do
				o = e(o, s.action), s = s.next;
			while (s !== i);
			Cr(o, t.memoizedState) || (ic = !0), t.memoizedState = o, t.baseQueue === null && (t.baseState = o), n.lastRenderedState = o;
		}
		return [o, r];
	}
	function Bo(e, t, n) {
		var r = B, i = jo(), o = z;
		if (o) {
			if (n === void 0) throw Error(a(407));
			n = n();
		} else n = t();
		var s = !Cr((V || i).memoizedState, n);
		if (s && (i.memoizedState = n, ic = !0), i = i.queue, ds(Uo.bind(null, r, i, e), [e]), i.getSnapshot !== t || s || mo !== null && mo.memoizedState.tag & 1) {
			if (r.flags |= 2048, os(9, { destroy: void 0 }, Ho.bind(null, r, i, n, t), null), K === null) throw Error(a(349));
			o || po & 127 || Vo(r, t, n);
		}
		return n;
	}
	function Vo(e, t, n) {
		e.flags |= 16384, e = {
			getSnapshot: t,
			value: n
		}, t = B.updateQueue, t === null ? (t = Mo(), B.updateQueue = t, t.stores = [e]) : (n = t.stores, n === null ? t.stores = [e] : n.push(e));
	}
	function Ho(e, t, n, r) {
		t.value = n, t.getSnapshot = r, Wo(t) && Go(e);
	}
	function Uo(e, t, n) {
		return n(function() {
			Wo(t) && Go(e);
		});
	}
	function Wo(e) {
		var t = e.getSnapshot;
		e = e.value;
		try {
			var n = t();
			return !Cr(e, n);
		} catch {
			return !0;
		}
	}
	function Go(e) {
		var t = ii(e, 2);
		t !== null && hu(t, e, 2);
	}
	function Ko(e) {
		var t = Ao();
		if (typeof e == "function") {
			var n = e;
			if (e = n(), _o) {
				He(!0);
				try {
					n();
				} finally {
					He(!1);
				}
			}
		}
		return t.memoizedState = t.baseState = e, t.queue = {
			pending: null,
			lanes: 0,
			dispatch: null,
			lastRenderedReducer: Io,
			lastRenderedState: e
		}, t;
	}
	function qo(e, t, n, r) {
		return e.baseState = n, Ro(e, V, typeof r == "function" ? r : Io);
	}
	function Jo(e, t, n, r, i) {
		if (Is(e)) throw Error(a(485));
		if (e = t.action, e !== null) {
			var o = {
				payload: i,
				action: e,
				next: null,
				isTransition: !0,
				status: "pending",
				value: null,
				reason: null,
				listeners: [],
				then: function(e) {
					o.listeners.push(e);
				}
			};
			O.T === null ? o.isTransition = !1 : n(!0), r(o), n = t.pending, n === null ? (o.next = t.pending = o, Yo(t, o)) : (o.next = n.next, t.pending = n.next = o);
		}
	}
	function Yo(e, t) {
		var n = t.action, r = t.payload, i = e.state;
		if (t.isTransition) {
			var a = O.T, o = {};
			O.T = o;
			try {
				var s = n(i, r), c = O.S;
				c !== null && c(o, s), Xo(e, t, s);
			} catch (n) {
				Qo(e, t, n);
			} finally {
				a !== null && o.types !== null && (a.types = o.types), O.T = a;
			}
		} else try {
			a = n(i, r), Xo(e, t, a);
		} catch (n) {
			Qo(e, t, n);
		}
	}
	function Xo(e, t, n) {
		typeof n == "object" && n && typeof n.then == "function" ? n.then(function(n) {
			Zo(e, t, n);
		}, function(n) {
			return Qo(e, t, n);
		}) : Zo(e, t, n);
	}
	function Zo(e, t, n) {
		t.status = "fulfilled", t.value = n, $o(t), e.state = n, t = e.pending, t !== null && (n = t.next, n === t ? e.pending = null : (n = n.next, t.next = n, Yo(e, n)));
	}
	function Qo(e, t, n) {
		var r = e.pending;
		if (e.pending = null, r !== null) {
			r = r.next;
			do
				t.status = "rejected", t.reason = n, $o(t), t = t.next;
			while (t !== r);
		}
		e.action = null;
	}
	function $o(e) {
		e = e.listeners;
		for (var t = 0; t < e.length; t++) (0, e[t])();
	}
	function es(e, t) {
		return t;
	}
	function ts(e, t) {
		if (z) {
			var n = K.formState;
			if (n !== null) {
				a: {
					var r = B;
					if (z) {
						if (R) {
							b: {
								for (var i = R, a = Ii; i.nodeType !== 8;) {
									if (!a) {
										i = null;
										break b;
									}
									if (i = cf(i.nextSibling), i === null) {
										i = null;
										break b;
									}
								}
								a = i.data, i = a === "F!" || a === "F" ? i : null;
							}
							if (i) {
								R = cf(i.nextSibling), r = i.data === "F!";
								break a;
							}
						}
						Ri(r);
					}
					r = !1;
				}
				r && (t = n[0]);
			}
		}
		return n = Ao(), n.memoizedState = n.baseState = t, r = {
			pending: null,
			lanes: 0,
			dispatch: null,
			lastRenderedReducer: es,
			lastRenderedState: t
		}, n.queue = r, n = Ns.bind(null, B, r), r.dispatch = n, r = Ko(!1), a = Fs.bind(null, B, !1, r.queue), r = Ao(), i = {
			state: t,
			dispatch: null,
			action: e,
			pending: null
		}, r.queue = i, n = Jo.bind(null, B, i, a, n), i.dispatch = n, r.memoizedState = e, [
			t,
			n,
			!1
		];
	}
	function ns(e) {
		return rs(jo(), V, e);
	}
	function rs(e, t, n) {
		if (t = Ro(e, t, es)[0], e = Lo(Io)[0], typeof t == "object" && t && typeof t.then == "function") try {
			var r = No(t);
		} catch (e) {
			throw e === Sa ? wa : e;
		}
		else r = t;
		t = jo();
		var i = t.queue, a = i.dispatch;
		return n !== t.memoizedState && (B.flags |= 2048, os(9, { destroy: void 0 }, is.bind(null, i, n), null)), [
			r,
			a,
			e
		];
	}
	function is(e, t) {
		e.action = t;
	}
	function as(e) {
		var t = jo(), n = V;
		if (n !== null) return rs(t, n, e);
		jo(), t = t.memoizedState, n = jo();
		var r = n.queue.dispatch;
		return n.memoizedState = e, [
			t,
			r,
			!1
		];
	}
	function os(e, t, n, r) {
		return e = {
			tag: e,
			create: n,
			deps: r,
			inst: t,
			next: null
		}, t = B.updateQueue, t === null && (t = Mo(), B.updateQueue = t), n = t.lastEffect, n === null ? t.lastEffect = e.next = e : (r = n.next, n.next = e, e.next = r, t.lastEffect = e), e;
	}
	function ss() {
		return jo().memoizedState;
	}
	function cs(e, t, n, r) {
		var i = Ao();
		B.flags |= e, i.memoizedState = os(1 | t, { destroy: void 0 }, n, r === void 0 ? null : r);
	}
	function ls(e, t, n, r) {
		var i = jo();
		r = r === void 0 ? null : r;
		var a = i.memoizedState.inst;
		V !== null && r !== null && So(r, V.memoizedState.deps) ? i.memoizedState = os(t, a, n, r) : (B.flags |= e, i.memoizedState = os(1 | t, a, n, r));
	}
	function us(e, t) {
		cs(8390656, 8, e, t);
	}
	function ds(e, t) {
		ls(2048, 8, e, t);
	}
	function fs(e) {
		B.flags |= 4;
		var t = B.updateQueue;
		if (t === null) t = Mo(), B.updateQueue = t, t.events = [e];
		else {
			var n = t.events;
			n === null ? t.events = [e] : n.push(e);
		}
	}
	function ps(e) {
		var t = jo().memoizedState;
		return fs({
			ref: t,
			nextImpl: e
		}), function() {
			if (G & 2) throw Error(a(440));
			return t.impl.apply(void 0, arguments);
		};
	}
	function ms(e, t) {
		return ls(4, 2, e, t);
	}
	function hs(e, t) {
		return ls(4, 4, e, t);
	}
	function gs(e, t) {
		if (typeof t == "function") {
			e = e();
			var n = t(e);
			return function() {
				typeof n == "function" ? n() : t(null);
			};
		}
		if (t != null) return e = e(), t.current = e, function() {
			t.current = null;
		};
	}
	function _s(e, t, n) {
		n = n == null ? null : n.concat([e]), ls(4, 4, gs.bind(null, t, e), n);
	}
	function vs() {}
	function ys(e, t) {
		var n = jo();
		t = t === void 0 ? null : t;
		var r = n.memoizedState;
		return t !== null && So(t, r[1]) ? r[0] : (n.memoizedState = [e, t], e);
	}
	function bs(e, t) {
		var n = jo();
		t = t === void 0 ? null : t;
		var r = n.memoizedState;
		if (t !== null && So(t, r[1])) return r[0];
		if (r = e(), _o) {
			He(!0);
			try {
				e();
			} finally {
				He(!1);
			}
		}
		return n.memoizedState = [r, t], r;
	}
	function xs(e, t, n) {
		return n === void 0 || po & 1073741824 && !(J & 261930) ? e.memoizedState = t : (e.memoizedState = n, e = mu(), B.lanes |= e, Gl |= e, n);
	}
	function Ss(e, t, n, r) {
		return Cr(n, t) ? n : Qa.current === null ? !(po & 42) || po & 1073741824 && !(J & 261930) ? (ic = !0, e.memoizedState = n) : (e = mu(), B.lanes |= e, Gl |= e, t) : (e = xs(e, n, r), Cr(e, t) || (ic = !0), e);
	}
	function Cs(e, t, n, r, i) {
		var a = k.p;
		k.p = a !== 0 && 8 > a ? a : 8;
		var o = O.T, s = {};
		O.T = s, Fs(e, !1, t, n);
		try {
			var c = i(), l = O.S;
			l !== null && l(s, c), typeof c == "object" && c && typeof c.then == "function" ? Ps(e, t, ga(c, r), pu(e)) : Ps(e, t, r, pu(e));
		} catch (n) {
			Ps(e, t, {
				then: function() {},
				status: "rejected",
				reason: n
			}, pu());
		} finally {
			k.p = a, o !== null && s.types !== null && (o.types = s.types), O.T = o;
		}
	}
	function ws() {}
	function Ts(e, t, n, r) {
		if (e.tag !== 5) throw Error(a(476));
		var i = Es(e).queue;
		Cs(e, i, t, ce, n === null ? ws : function() {
			return Ds(e), n(r);
		});
	}
	function Es(e) {
		var t = e.memoizedState;
		if (t !== null) return t;
		t = {
			memoizedState: ce,
			baseState: ce,
			baseQueue: null,
			queue: {
				pending: null,
				lanes: 0,
				dispatch: null,
				lastRenderedReducer: Io,
				lastRenderedState: ce
			},
			next: null
		};
		var n = {};
		return t.next = {
			memoizedState: n,
			baseState: n,
			baseQueue: null,
			queue: {
				pending: null,
				lanes: 0,
				dispatch: null,
				lastRenderedReducer: Io,
				lastRenderedState: n
			},
			next: null
		}, e.memoizedState = t, e = e.alternate, e !== null && (e.memoizedState = t), t;
	}
	function Ds(e) {
		var t = Es(e);
		t.next === null && (t = e.alternate.memoizedState), Ps(e, t.next.queue, {}, pu());
	}
	function Os() {
		return ta(Qf);
	}
	function ks() {
		return jo().memoizedState;
	}
	function As() {
		return jo().memoizedState;
	}
	function js(e) {
		for (var t = e.return; t !== null;) {
			switch (t.tag) {
				case 24:
				case 3:
					var n = pu();
					e = Ua(n);
					var r = Wa(t, e, n);
					r !== null && (hu(r, t, n), Ga(r, t, n)), t = { cache: ca() }, e.payload = t;
					return;
			}
			t = t.return;
		}
	}
	function Ms(e, t, n) {
		var r = pu();
		n = {
			lane: r,
			revertLane: 0,
			gesture: null,
			action: n,
			hasEagerState: !1,
			eagerState: null,
			next: null
		}, Is(e) ? Ls(t, n) : (n = ri(e, t, n, r), n !== null && (hu(n, e, r), Rs(n, t, r)));
	}
	function Ns(e, t, n) {
		Ps(e, t, n, pu());
	}
	function Ps(e, t, n, r) {
		var i = {
			lane: r,
			revertLane: 0,
			gesture: null,
			action: n,
			hasEagerState: !1,
			eagerState: null,
			next: null
		};
		if (Is(e)) Ls(t, i);
		else {
			var a = e.alternate;
			if (e.lanes === 0 && (a === null || a.lanes === 0) && (a = t.lastRenderedReducer, a !== null)) try {
				var o = t.lastRenderedState, s = a(o, n);
				if (i.hasEagerState = !0, i.eagerState = s, Cr(s, o)) return ni(e, t, i, 0), K === null && ti(), !1;
			} catch {}
			if (n = ri(e, t, i, r), n !== null) return hu(n, e, r), Rs(n, t, r), !0;
		}
		return !1;
	}
	function Fs(e, t, n, r) {
		if (r = {
			lane: 2,
			revertLane: dd(),
			gesture: null,
			action: r,
			hasEagerState: !1,
			eagerState: null,
			next: null
		}, Is(e)) {
			if (t) throw Error(a(479));
		} else t = ri(e, n, r, 2), t !== null && hu(t, e, 2);
	}
	function Is(e) {
		var t = e.alternate;
		return e === B || t !== null && t === B;
	}
	function Ls(e, t) {
		go = ho = !0;
		var n = e.pending;
		n === null ? t.next = t : (t.next = n.next, n.next = t), e.pending = t;
	}
	function Rs(e, t, n) {
		if (n & 4194048) {
			var r = t.lanes;
			r &= e.pendingLanes, n |= r, t.lanes = n, at(e, n);
		}
	}
	var zs = {
		readContext: ta,
		use: Po,
		useCallback: H,
		useContext: H,
		useEffect: H,
		useImperativeHandle: H,
		useLayoutEffect: H,
		useInsertionEffect: H,
		useMemo: H,
		useReducer: H,
		useRef: H,
		useState: H,
		useDebugValue: H,
		useDeferredValue: H,
		useTransition: H,
		useSyncExternalStore: H,
		useId: H,
		useHostTransitionStatus: H,
		useFormState: H,
		useActionState: H,
		useOptimistic: H,
		useMemoCache: H,
		useCacheRefresh: H
	};
	zs.useEffectEvent = H;
	var Bs = {
		readContext: ta,
		use: Po,
		useCallback: function(e, t) {
			return Ao().memoizedState = [e, t === void 0 ? null : t], e;
		},
		useContext: ta,
		useEffect: us,
		useImperativeHandle: function(e, t, n) {
			n = n == null ? null : n.concat([e]), cs(4194308, 4, gs.bind(null, t, e), n);
		},
		useLayoutEffect: function(e, t) {
			return cs(4194308, 4, e, t);
		},
		useInsertionEffect: function(e, t) {
			cs(4, 2, e, t);
		},
		useMemo: function(e, t) {
			var n = Ao();
			t = t === void 0 ? null : t;
			var r = e();
			if (_o) {
				He(!0);
				try {
					e();
				} finally {
					He(!1);
				}
			}
			return n.memoizedState = [r, t], r;
		},
		useReducer: function(e, t, n) {
			var r = Ao();
			if (n !== void 0) {
				var i = n(t);
				if (_o) {
					He(!0);
					try {
						n(t);
					} finally {
						He(!1);
					}
				}
			} else i = t;
			return r.memoizedState = r.baseState = i, e = {
				pending: null,
				lanes: 0,
				dispatch: null,
				lastRenderedReducer: e,
				lastRenderedState: i
			}, r.queue = e, e = e.dispatch = Ms.bind(null, B, e), [r.memoizedState, e];
		},
		useRef: function(e) {
			var t = Ao();
			return e = { current: e }, t.memoizedState = e;
		},
		useState: function(e) {
			e = Ko(e);
			var t = e.queue, n = Ns.bind(null, B, t);
			return t.dispatch = n, [e.memoizedState, n];
		},
		useDebugValue: vs,
		useDeferredValue: function(e, t) {
			return xs(Ao(), e, t);
		},
		useTransition: function() {
			var e = Ko(!1);
			return e = Cs.bind(null, B, e.queue, !0, !1), Ao().memoizedState = e, [!1, e];
		},
		useSyncExternalStore: function(e, t, n) {
			var r = B, i = Ao();
			if (z) {
				if (n === void 0) throw Error(a(407));
				n = n();
			} else {
				if (n = t(), K === null) throw Error(a(349));
				J & 127 || Vo(r, t, n);
			}
			i.memoizedState = n;
			var o = {
				value: n,
				getSnapshot: t
			};
			return i.queue = o, us(Uo.bind(null, r, o, e), [e]), r.flags |= 2048, os(9, { destroy: void 0 }, Ho.bind(null, r, o, n, t), null), n;
		},
		useId: function() {
			var e = Ao(), t = K.identifierPrefix;
			if (z) {
				var n = Oi, r = Di;
				n = (r & ~(1 << 32 - Ue(r) - 1)).toString(32) + n, t = "_" + t + "R_" + n, n = vo++, 0 < n && (t += "H" + n.toString(32)), t += "_";
			} else n = xo++, t = "_" + t + "r_" + n.toString(32) + "_";
			return e.memoizedState = t;
		},
		useHostTransitionStatus: Os,
		useFormState: ts,
		useActionState: ts,
		useOptimistic: function(e) {
			var t = Ao();
			t.memoizedState = t.baseState = e;
			var n = {
				pending: null,
				lanes: 0,
				dispatch: null,
				lastRenderedReducer: null,
				lastRenderedState: null
			};
			return t.queue = n, t = Fs.bind(null, B, !0, n), n.dispatch = t, [e, t];
		},
		useMemoCache: Fo,
		useCacheRefresh: function() {
			return Ao().memoizedState = js.bind(null, B);
		},
		useEffectEvent: function(e) {
			var t = Ao(), n = { impl: e };
			return t.memoizedState = n, function() {
				if (G & 2) throw Error(a(440));
				return n.impl.apply(void 0, arguments);
			};
		}
	}, Vs = {
		readContext: ta,
		use: Po,
		useCallback: ys,
		useContext: ta,
		useEffect: ds,
		useImperativeHandle: _s,
		useInsertionEffect: ms,
		useLayoutEffect: hs,
		useMemo: bs,
		useReducer: Lo,
		useRef: ss,
		useState: function() {
			return Lo(Io);
		},
		useDebugValue: vs,
		useDeferredValue: function(e, t) {
			return Ss(jo(), V.memoizedState, e, t);
		},
		useTransition: function() {
			var e = Lo(Io)[0], t = jo().memoizedState;
			return [typeof e == "boolean" ? e : No(e), t];
		},
		useSyncExternalStore: Bo,
		useId: ks,
		useHostTransitionStatus: Os,
		useFormState: ns,
		useActionState: ns,
		useOptimistic: function(e, t) {
			return qo(jo(), V, e, t);
		},
		useMemoCache: Fo,
		useCacheRefresh: As
	};
	Vs.useEffectEvent = ps;
	var Hs = {
		readContext: ta,
		use: Po,
		useCallback: ys,
		useContext: ta,
		useEffect: ds,
		useImperativeHandle: _s,
		useInsertionEffect: ms,
		useLayoutEffect: hs,
		useMemo: bs,
		useReducer: zo,
		useRef: ss,
		useState: function() {
			return zo(Io);
		},
		useDebugValue: vs,
		useDeferredValue: function(e, t) {
			var n = jo();
			return V === null ? xs(n, e, t) : Ss(n, V.memoizedState, e, t);
		},
		useTransition: function() {
			var e = zo(Io)[0], t = jo().memoizedState;
			return [typeof e == "boolean" ? e : No(e), t];
		},
		useSyncExternalStore: Bo,
		useId: ks,
		useHostTransitionStatus: Os,
		useFormState: as,
		useActionState: as,
		useOptimistic: function(e, t) {
			var n = jo();
			return V === null ? (n.baseState = e, [e, n.queue.dispatch]) : qo(n, V, e, t);
		},
		useMemoCache: Fo,
		useCacheRefresh: As
	};
	Hs.useEffectEvent = ps;
	function Us(e, t, n, r) {
		t = e.memoizedState, n = n(r, t), n = n == null ? t : h({}, t, n), e.memoizedState = n, e.lanes === 0 && (e.updateQueue.baseState = n);
	}
	var Ws = {
		enqueueSetState: function(e, t, n) {
			e = e._reactInternals;
			var r = pu(), i = Ua(r);
			i.payload = t, n != null && (i.callback = n), t = Wa(e, i, r), t !== null && (hu(t, e, r), Ga(t, e, r));
		},
		enqueueReplaceState: function(e, t, n) {
			e = e._reactInternals;
			var r = pu(), i = Ua(r);
			i.tag = 1, i.payload = t, n != null && (i.callback = n), t = Wa(e, i, r), t !== null && (hu(t, e, r), Ga(t, e, r));
		},
		enqueueForceUpdate: function(e, t) {
			e = e._reactInternals;
			var n = pu(), r = Ua(n);
			r.tag = 2, t != null && (r.callback = t), t = Wa(e, r, n), t !== null && (hu(t, e, n), Ga(t, e, n));
		}
	};
	function Gs(e, t, n, r, i, a, o) {
		return e = e.stateNode, typeof e.shouldComponentUpdate == "function" ? e.shouldComponentUpdate(r, a, o) : t.prototype && t.prototype.isPureReactComponent ? !wr(n, r) || !wr(i, a) : !0;
	}
	function Ks(e, t, n, r) {
		e = t.state, typeof t.componentWillReceiveProps == "function" && t.componentWillReceiveProps(n, r), typeof t.UNSAFE_componentWillReceiveProps == "function" && t.UNSAFE_componentWillReceiveProps(n, r), t.state !== e && Ws.enqueueReplaceState(t, t.state, null);
	}
	function qs(e, t) {
		var n = t;
		if ("ref" in t) for (var r in n = {}, t) r !== "ref" && (n[r] = t[r]);
		if (e = e.defaultProps) for (var i in n === t && (n = h({}, n)), e) n[i] === void 0 && (n[i] = e[i]);
		return n;
	}
	function Js(e) {
		Zr(e);
	}
	function Ys(e) {
		console.error(e);
	}
	function Xs(e) {
		Zr(e);
	}
	function Zs(e, t) {
		try {
			var n = e.onUncaughtError;
			n(t.value, { componentStack: t.stack });
		} catch (e) {
			setTimeout(function() {
				throw e;
			});
		}
	}
	function Qs(e, t, n) {
		try {
			var r = e.onCaughtError;
			r(n.value, {
				componentStack: n.stack,
				errorBoundary: t.tag === 1 ? t.stateNode : null
			});
		} catch (e) {
			setTimeout(function() {
				throw e;
			});
		}
	}
	function $s(e, t, n) {
		return n = Ua(n), n.tag = 3, n.payload = { element: null }, n.callback = function() {
			Zs(e, t);
		}, n;
	}
	function ec(e) {
		return e = Ua(e), e.tag = 3, e;
	}
	function tc(e, t, n, r) {
		var i = n.type.getDerivedStateFromError;
		if (typeof i == "function") {
			var a = r.value;
			e.payload = function() {
				return i(a);
			}, e.callback = function() {
				Qs(t, n, r);
			};
		}
		var o = n.stateNode;
		o !== null && typeof o.componentDidCatch == "function" && (e.callback = function() {
			Qs(t, n, r), typeof i != "function" && (ru === null ? ru = /* @__PURE__ */ new Set([this]) : ru.add(this));
			var e = r.stack;
			this.componentDidCatch(r.value, { componentStack: e === null ? "" : e });
		});
	}
	function nc(e, t, n, r, i) {
		if (n.flags |= 32768, typeof r == "object" && r && typeof r.then == "function") {
			if (t = n.alternate, t !== null && Qi(t, n, i, !0), n = ro.current, n !== null) {
				switch (n.tag) {
					case 31:
					case 13: return io === null ? Du() : n.alternate === null && X === 0 && (X = 3), n.flags &= -257, n.flags |= 65536, n.lanes = i, r === Ta ? n.flags |= 16384 : (t = n.updateQueue, t === null ? n.updateQueue = /* @__PURE__ */ new Set([r]) : t.add(r), Gu(e, r, i)), !1;
					case 22: return n.flags |= 65536, r === Ta ? n.flags |= 16384 : (t = n.updateQueue, t === null ? (t = {
						transitions: null,
						markerInstances: null,
						retryQueue: /* @__PURE__ */ new Set([r])
					}, n.updateQueue = t) : (n = t.retryQueue, n === null ? t.retryQueue = /* @__PURE__ */ new Set([r]) : n.add(r)), Gu(e, r, i)), !1;
				}
				throw Error(a(435, n.tag));
			}
			return Gu(e, r, i), Du(), !1;
		}
		if (z) return t = ro.current, t === null ? (r !== Li && (t = Error(a(423), { cause: r }), Wi(yi(t, n))), e = e.current.alternate, e.flags |= 65536, i &= -i, e.lanes |= i, r = yi(r, n), i = $s(e.stateNode, r, i), Ka(e, i), X !== 4 && (X = 2)) : (!(t.flags & 65536) && (t.flags |= 256), t.flags |= 65536, t.lanes = i, r !== Li && (e = Error(a(422), { cause: r }), Wi(yi(e, n)))), !1;
		var o = Error(a(520), { cause: r });
		if (o = yi(o, n), Xl === null ? Xl = [o] : Xl.push(o), X !== 4 && (X = 2), t === null) return !0;
		r = yi(r, n), n = t;
		do {
			switch (n.tag) {
				case 3: return n.flags |= 65536, e = i & -i, n.lanes |= e, e = $s(n.stateNode, r, e), Ka(n, e), !1;
				case 1: if (t = n.type, o = n.stateNode, !(n.flags & 128) && (typeof t.getDerivedStateFromError == "function" || o !== null && typeof o.componentDidCatch == "function" && (ru === null || !ru.has(o)))) return n.flags |= 65536, i &= -i, n.lanes |= i, i = ec(i), tc(i, e, n, r), Ka(n, i), !1;
			}
			n = n.return;
		} while (n !== null);
		return !1;
	}
	var rc = Error(a(461)), ic = !1;
	function ac(e, t, n, r) {
		t.child = e === null ? za(t, null, n, r) : Ra(t, e.child, n, r);
	}
	function oc(e, t, n, r, i) {
		n = n.render;
		var a = t.ref;
		if ("ref" in r) {
			var o = {};
			for (var s in r) s !== "ref" && (o[s] = r[s]);
		} else o = r;
		return ea(t), r = Co(e, t, n, o, a, i), s = Do(), e !== null && !ic ? (Oo(e, t, i), Ac(e, t, i)) : (z && s && ji(t), t.flags |= 1, ac(e, t, r, i), t.child);
	}
	function sc(e, t, n, r, i) {
		if (e === null) {
			var a = n.type;
			return typeof a == "function" && !ui(a) && a.defaultProps === void 0 && n.compare === null ? (t.tag = 15, t.type = a, cc(e, t, a, r, i)) : (e = pi(n.type, null, r, t, t.mode, i), e.ref = t.ref, e.return = t, t.child = e);
		}
		if (a = e.child, !jc(e, i)) {
			var o = a.memoizedProps;
			if (n = n.compare, n = n === null ? wr : n, n(o, r) && e.ref === t.ref) return Ac(e, t, i);
		}
		return t.flags |= 1, e = di(a, r), e.ref = t.ref, e.return = t, t.child = e;
	}
	function cc(e, t, n, r, i) {
		if (e !== null) {
			var a = e.memoizedProps;
			if (wr(a, r) && e.ref === t.ref) if (ic = !1, t.pendingProps = r = a, jc(e, i)) e.flags & 131072 && (ic = !0);
			else return t.lanes = e.lanes, Ac(e, t, i);
		}
		return gc(e, t, n, r, i);
	}
	function lc(e, t, n, r) {
		var i = r.children, a = e === null ? null : e.memoizedState;
		if (e === null && t.stateNode === null && (t.stateNode = {
			_visibility: 1,
			_pendingMarkers: null,
			_retryCache: null,
			_transitions: null
		}), r.mode === "hidden") {
			if (t.flags & 128) {
				if (a = a === null ? n : a.baseLanes | n, e !== null) {
					for (r = t.child = e.child, i = 0; r !== null;) i = i | r.lanes | r.childLanes, r = r.sibling;
					r = i & ~a;
				} else r = 0, t.child = null;
				return dc(e, t, a, n, r);
			}
			if (n & 536870912) t.memoizedState = {
				baseLanes: 0,
				cachePool: null
			}, e !== null && ba(t, a === null ? null : a.cachePool), a === null ? to() : eo(t, a), so(t);
			else return r = t.lanes = 536870912, dc(e, t, a === null ? n : a.baseLanes | n, n, r);
		} else a === null ? (e !== null && ba(t, null), to(), co(t)) : (ba(t, a.cachePool), eo(t, a), co(t), t.memoizedState = null);
		return ac(e, t, i, n), t.child;
	}
	function uc(e, t) {
		return e !== null && e.tag === 22 || t.stateNode !== null || (t.stateNode = {
			_visibility: 1,
			_pendingMarkers: null,
			_retryCache: null,
			_transitions: null
		}), t.sibling;
	}
	function dc(e, t, n, r, i) {
		var a = ya();
		return a = a === null ? null : {
			parent: sa._currentValue,
			pool: a
		}, t.memoizedState = {
			baseLanes: n,
			cachePool: a
		}, e !== null && ba(t, null), to(), so(t), e !== null && Qi(e, t, r, !0), t.childLanes = i, null;
	}
	function fc(e, t) {
		return t = Tc({
			mode: t.mode,
			children: t.children
		}, e.mode), t.ref = e.ref, e.child = t, t.return = e, t;
	}
	function pc(e, t, n) {
		return Ra(t, e.child, null, n), e = fc(t, t.pendingProps), e.flags |= 2, lo(t), t.memoizedState = null, e;
	}
	function mc(e, t, n) {
		var r = t.pendingProps, i = (t.flags & 128) != 0;
		if (t.flags &= -129, e === null) {
			if (z) {
				if (r.mode === "hidden") return e = fc(t, r), t.lanes = 536870912, uc(null, e);
				if (oo(t), (e = R) ? (e = rf(e, Ii), e = e !== null && e.data === "&" ? e : null, e !== null && (t.memoizedState = {
					dehydrated: e,
					treeContext: Ei === null ? null : {
						id: Di,
						overflow: Oi
					},
					retryLane: 536870912,
					hydrationErrors: null
				}, n = gi(e), n.return = t, t.child = n, Pi = t, R = null)) : e = null, e === null) throw Ri(t);
				return t.lanes = 536870912, null;
			}
			return fc(t, r);
		}
		var o = e.memoizedState;
		if (o !== null) {
			var s = o.dehydrated;
			if (oo(t), i) if (t.flags & 256) t.flags &= -257, t = pc(e, t, n);
			else if (t.memoizedState !== null) t.child = e.child, t.flags |= 128, t = null;
			else throw Error(a(558));
			else if (ic || Qi(e, t, n, !1), i = (n & e.childLanes) !== 0, ic || i) {
				if (r = K, r !== null && (s = ot(r, n), s !== 0 && s !== o.retryLane)) throw o.retryLane = s, ii(e, s), hu(r, e, s), rc;
				Du(), t = pc(e, t, n);
			} else e = o.treeContext, R = cf(s.nextSibling), Pi = t, z = !0, Fi = null, Ii = !1, e !== null && Ni(t, e), t = fc(t, r), t.flags |= 4096;
			return t;
		}
		return e = di(e.child, {
			mode: r.mode,
			children: r.children
		}), e.ref = t.ref, t.child = e, e.return = t, e;
	}
	function hc(e, t) {
		var n = t.ref;
		if (n === null) e !== null && e.ref !== null && (t.flags |= 4194816);
		else {
			if (typeof n != "function" && typeof n != "object") throw Error(a(284));
			(e === null || e.ref !== n) && (t.flags |= 4194816);
		}
	}
	function gc(e, t, n, r, i) {
		return ea(t), n = Co(e, t, n, r, void 0, i), r = Do(), e !== null && !ic ? (Oo(e, t, i), Ac(e, t, i)) : (z && r && ji(t), t.flags |= 1, ac(e, t, n, i), t.child);
	}
	function _c(e, t, n, r, i, a) {
		return ea(t), t.updateQueue = null, n = To(t, r, n, i), wo(e), r = Do(), e !== null && !ic ? (Oo(e, t, a), Ac(e, t, a)) : (z && r && ji(t), t.flags |= 1, ac(e, t, n, a), t.child);
	}
	function vc(e, t, n, r, i) {
		if (ea(t), t.stateNode === null) {
			var a = si, o = n.contextType;
			typeof o == "object" && o && (a = ta(o)), a = new n(r, a), t.memoizedState = a.state !== null && a.state !== void 0 ? a.state : null, a.updater = Ws, t.stateNode = a, a._reactInternals = t, a = t.stateNode, a.props = r, a.state = t.memoizedState, a.refs = {}, Va(t), o = n.contextType, a.context = typeof o == "object" && o ? ta(o) : si, a.state = t.memoizedState, o = n.getDerivedStateFromProps, typeof o == "function" && (Us(t, n, o, r), a.state = t.memoizedState), typeof n.getDerivedStateFromProps == "function" || typeof a.getSnapshotBeforeUpdate == "function" || typeof a.UNSAFE_componentWillMount != "function" && typeof a.componentWillMount != "function" || (o = a.state, typeof a.componentWillMount == "function" && a.componentWillMount(), typeof a.UNSAFE_componentWillMount == "function" && a.UNSAFE_componentWillMount(), o !== a.state && Ws.enqueueReplaceState(a, a.state, null), Ya(t, r, a, i), Ja(), a.state = t.memoizedState), typeof a.componentDidMount == "function" && (t.flags |= 4194308), r = !0;
		} else if (e === null) {
			a = t.stateNode;
			var s = t.memoizedProps, c = qs(n, s);
			a.props = c;
			var l = a.context, u = n.contextType;
			o = si, typeof u == "object" && u && (o = ta(u));
			var d = n.getDerivedStateFromProps;
			u = typeof d == "function" || typeof a.getSnapshotBeforeUpdate == "function", s = t.pendingProps !== s, u || typeof a.UNSAFE_componentWillReceiveProps != "function" && typeof a.componentWillReceiveProps != "function" || (s || l !== o) && Ks(t, a, r, o), Ba = !1;
			var f = t.memoizedState;
			a.state = f, Ya(t, r, a, i), Ja(), l = t.memoizedState, s || f !== l || Ba ? (typeof d == "function" && (Us(t, n, d, r), l = t.memoizedState), (c = Ba || Gs(t, n, c, r, f, l, o)) ? (u || typeof a.UNSAFE_componentWillMount != "function" && typeof a.componentWillMount != "function" || (typeof a.componentWillMount == "function" && a.componentWillMount(), typeof a.UNSAFE_componentWillMount == "function" && a.UNSAFE_componentWillMount()), typeof a.componentDidMount == "function" && (t.flags |= 4194308)) : (typeof a.componentDidMount == "function" && (t.flags |= 4194308), t.memoizedProps = r, t.memoizedState = l), a.props = r, a.state = l, a.context = o, r = c) : (typeof a.componentDidMount == "function" && (t.flags |= 4194308), r = !1);
		} else {
			a = t.stateNode, Ha(e, t), o = t.memoizedProps, u = qs(n, o), a.props = u, d = t.pendingProps, f = a.context, l = n.contextType, c = si, typeof l == "object" && l && (c = ta(l)), s = n.getDerivedStateFromProps, (l = typeof s == "function" || typeof a.getSnapshotBeforeUpdate == "function") || typeof a.UNSAFE_componentWillReceiveProps != "function" && typeof a.componentWillReceiveProps != "function" || (o !== d || f !== c) && Ks(t, a, r, c), Ba = !1, f = t.memoizedState, a.state = f, Ya(t, r, a, i), Ja();
			var p = t.memoizedState;
			o !== d || f !== p || Ba || e !== null && e.dependencies !== null && $i(e.dependencies) ? (typeof s == "function" && (Us(t, n, s, r), p = t.memoizedState), (u = Ba || Gs(t, n, u, r, f, p, c) || e !== null && e.dependencies !== null && $i(e.dependencies)) ? (l || typeof a.UNSAFE_componentWillUpdate != "function" && typeof a.componentWillUpdate != "function" || (typeof a.componentWillUpdate == "function" && a.componentWillUpdate(r, p, c), typeof a.UNSAFE_componentWillUpdate == "function" && a.UNSAFE_componentWillUpdate(r, p, c)), typeof a.componentDidUpdate == "function" && (t.flags |= 4), typeof a.getSnapshotBeforeUpdate == "function" && (t.flags |= 1024)) : (typeof a.componentDidUpdate != "function" || o === e.memoizedProps && f === e.memoizedState || (t.flags |= 4), typeof a.getSnapshotBeforeUpdate != "function" || o === e.memoizedProps && f === e.memoizedState || (t.flags |= 1024), t.memoizedProps = r, t.memoizedState = p), a.props = r, a.state = p, a.context = c, r = u) : (typeof a.componentDidUpdate != "function" || o === e.memoizedProps && f === e.memoizedState || (t.flags |= 4), typeof a.getSnapshotBeforeUpdate != "function" || o === e.memoizedProps && f === e.memoizedState || (t.flags |= 1024), r = !1);
		}
		return a = r, hc(e, t), r = (t.flags & 128) != 0, a || r ? (a = t.stateNode, n = r && typeof n.getDerivedStateFromError != "function" ? null : a.render(), t.flags |= 1, e !== null && r ? (t.child = Ra(t, e.child, null, i), t.child = Ra(t, null, n, i)) : ac(e, t, n, i), t.memoizedState = a.state, e = t.child) : e = Ac(e, t, i), e;
	}
	function yc(e, t, n, r) {
		return Hi(), t.flags |= 256, ac(e, t, n, r), t.child;
	}
	var bc = {
		dehydrated: null,
		treeContext: null,
		retryLane: 0,
		hydrationErrors: null
	};
	function xc(e) {
		return {
			baseLanes: e,
			cachePool: xa()
		};
	}
	function Sc(e, t, n) {
		return e = e === null ? 0 : e.childLanes & ~n, t && (e |= Jl), e;
	}
	function Cc(e, t, n) {
		var r = t.pendingProps, i = !1, o = (t.flags & 128) != 0, s;
		if ((s = o) || (s = e !== null && e.memoizedState === null ? !1 : (uo.current & 2) != 0), s && (i = !0, t.flags &= -129), s = (t.flags & 32) != 0, t.flags &= -33, e === null) {
			if (z) {
				if (i ? ao(t) : co(t), (e = R) ? (e = rf(e, Ii), e = e !== null && e.data !== "&" ? e : null, e !== null && (t.memoizedState = {
					dehydrated: e,
					treeContext: Ei === null ? null : {
						id: Di,
						overflow: Oi
					},
					retryLane: 536870912,
					hydrationErrors: null
				}, n = gi(e), n.return = t, t.child = n, Pi = t, R = null)) : e = null, e === null) throw Ri(t);
				return of(e) ? t.lanes = 32 : t.lanes = 536870912, null;
			}
			var c = r.children;
			return r = r.fallback, i ? (co(t), i = t.mode, c = Tc({
				mode: "hidden",
				children: c
			}, i), r = mi(r, i, n, null), c.return = t, r.return = t, c.sibling = r, t.child = c, r = t.child, r.memoizedState = xc(n), r.childLanes = Sc(e, s, n), t.memoizedState = bc, uc(null, r)) : (ao(t), wc(t, c));
		}
		var l = e.memoizedState;
		if (l !== null && (c = l.dehydrated, c !== null)) {
			if (o) t.flags & 256 ? (ao(t), t.flags &= -257, t = Ec(e, t, n)) : t.memoizedState === null ? (co(t), c = r.fallback, i = t.mode, r = Tc({
				mode: "visible",
				children: r.children
			}, i), c = mi(c, i, n, null), c.flags |= 2, r.return = t, c.return = t, r.sibling = c, t.child = r, Ra(t, e.child, null, n), r = t.child, r.memoizedState = xc(n), r.childLanes = Sc(e, s, n), t.memoizedState = bc, t = uc(null, r)) : (co(t), t.child = e.child, t.flags |= 128, t = null);
			else if (ao(t), of(c)) {
				if (s = c.nextSibling && c.nextSibling.dataset, s) var u = s.dgst;
				s = u, r = Error(a(419)), r.stack = "", r.digest = s, Wi({
					value: r,
					source: null,
					stack: null
				}), t = Ec(e, t, n);
			} else if (ic || Qi(e, t, n, !1), s = (n & e.childLanes) !== 0, ic || s) {
				if (s = K, s !== null && (r = ot(s, n), r !== 0 && r !== l.retryLane)) throw l.retryLane = r, ii(e, r), hu(s, e, r), rc;
				af(c) || Du(), t = Ec(e, t, n);
			} else af(c) ? (t.flags |= 192, t.child = e.child, t = null) : (e = l.treeContext, R = cf(c.nextSibling), Pi = t, z = !0, Fi = null, Ii = !1, e !== null && Ni(t, e), t = wc(t, r.children), t.flags |= 4096);
			return t;
		}
		return i ? (co(t), c = r.fallback, i = t.mode, l = e.child, u = l.sibling, r = di(l, {
			mode: "hidden",
			children: r.children
		}), r.subtreeFlags = l.subtreeFlags & 65011712, u === null ? (c = mi(c, i, n, null), c.flags |= 2) : c = di(u, c), c.return = t, r.return = t, r.sibling = c, t.child = r, uc(null, r), r = t.child, c = e.child.memoizedState, c === null ? c = xc(n) : (i = c.cachePool, i === null ? i = xa() : (l = sa._currentValue, i = i.parent === l ? i : {
			parent: l,
			pool: l
		}), c = {
			baseLanes: c.baseLanes | n,
			cachePool: i
		}), r.memoizedState = c, r.childLanes = Sc(e, s, n), t.memoizedState = bc, uc(e.child, r)) : (ao(t), n = e.child, e = n.sibling, n = di(n, {
			mode: "visible",
			children: r.children
		}), n.return = t, n.sibling = null, e !== null && (s = t.deletions, s === null ? (t.deletions = [e], t.flags |= 16) : s.push(e)), t.child = n, t.memoizedState = null, n);
	}
	function wc(e, t) {
		return t = Tc({
			mode: "visible",
			children: t
		}, e.mode), t.return = e, e.child = t;
	}
	function Tc(e, t) {
		return e = li(22, e, null, t), e.lanes = 0, e;
	}
	function Ec(e, t, n) {
		return Ra(t, e.child, null, n), e = wc(t, t.pendingProps.children), e.flags |= 2, t.memoizedState = null, e;
	}
	function Dc(e, t, n) {
		e.lanes |= t;
		var r = e.alternate;
		r !== null && (r.lanes |= t), Xi(e.return, t, n);
	}
	function Oc(e, t, n, r, i, a) {
		var o = e.memoizedState;
		o === null ? e.memoizedState = {
			isBackwards: t,
			rendering: null,
			renderingStartTime: 0,
			last: r,
			tail: n,
			tailMode: i,
			treeForkCount: a
		} : (o.isBackwards = t, o.rendering = null, o.renderingStartTime = 0, o.last = r, o.tail = n, o.tailMode = i, o.treeForkCount = a);
	}
	function kc(e, t, n) {
		var r = t.pendingProps, i = r.revealOrder, a = r.tail;
		r = r.children;
		var o = uo.current, s = (o & 2) != 0;
		if (s ? (o = o & 1 | 2, t.flags |= 128) : o &= 1, j(uo, o), ac(e, t, r, n), r = z ? Ci : 0, !s && e !== null && e.flags & 128) a: for (e = t.child; e !== null;) {
			if (e.tag === 13) e.memoizedState !== null && Dc(e, n, t);
			else if (e.tag === 19) Dc(e, n, t);
			else if (e.child !== null) {
				e.child.return = e, e = e.child;
				continue;
			}
			if (e === t) break a;
			for (; e.sibling === null;) {
				if (e.return === null || e.return === t) break a;
				e = e.return;
			}
			e.sibling.return = e.return, e = e.sibling;
		}
		switch (i) {
			case "forwards":
				for (n = t.child, i = null; n !== null;) e = n.alternate, e !== null && fo(e) === null && (i = n), n = n.sibling;
				n = i, n === null ? (i = t.child, t.child = null) : (i = n.sibling, n.sibling = null), Oc(t, !1, i, n, a, r);
				break;
			case "backwards":
			case "unstable_legacy-backwards":
				for (n = null, i = t.child, t.child = null; i !== null;) {
					if (e = i.alternate, e !== null && fo(e) === null) {
						t.child = i;
						break;
					}
					e = i.sibling, i.sibling = n, n = i, i = e;
				}
				Oc(t, !0, n, null, a, r);
				break;
			case "together":
				Oc(t, !1, null, null, void 0, r);
				break;
			default: t.memoizedState = null;
		}
		return t.child;
	}
	function Ac(e, t, n) {
		if (e !== null && (t.dependencies = e.dependencies), Gl |= t.lanes, (n & t.childLanes) === 0) if (e !== null) {
			if (Qi(e, t, n, !1), (n & t.childLanes) === 0) return null;
		} else return null;
		if (e !== null && t.child !== e.child) throw Error(a(153));
		if (t.child !== null) {
			for (e = t.child, n = di(e, e.pendingProps), t.child = n, n.return = t; e.sibling !== null;) e = e.sibling, n = n.sibling = di(e, e.pendingProps), n.return = t;
			n.sibling = null;
		}
		return t.child;
	}
	function jc(e, t) {
		return (e.lanes & t) === 0 ? (e = e.dependencies, !!(e !== null && $i(e))) : !0;
	}
	function Mc(e, t, n) {
		switch (t.tag) {
			case 3:
				ge(t, t.stateNode.containerInfo), Ji(t, sa, e.memoizedState.cache), Hi();
				break;
			case 27:
			case 5:
				ve(t);
				break;
			case 4:
				ge(t, t.stateNode.containerInfo);
				break;
			case 10:
				Ji(t, t.type, t.memoizedProps.value);
				break;
			case 31:
				if (t.memoizedState !== null) return t.flags |= 128, oo(t), null;
				break;
			case 13:
				var r = t.memoizedState;
				if (r !== null) return r.dehydrated === null ? (n & t.child.childLanes) === 0 ? (ao(t), e = Ac(e, t, n), e === null ? null : e.sibling) : Cc(e, t, n) : (ao(t), t.flags |= 128, null);
				ao(t);
				break;
			case 19:
				var i = (e.flags & 128) != 0;
				if (r = (n & t.childLanes) !== 0, r ||= (Qi(e, t, n, !1), (n & t.childLanes) !== 0), i) {
					if (r) return kc(e, t, n);
					t.flags |= 128;
				}
				if (i = t.memoizedState, i !== null && (i.rendering = null, i.tail = null, i.lastEffect = null), j(uo, uo.current), r) break;
				return null;
			case 22: return t.lanes = 0, lc(e, t, n, t.pendingProps);
			case 24: Ji(t, sa, e.memoizedState.cache);
		}
		return Ac(e, t, n);
	}
	function Nc(e, t, n) {
		if (e !== null) if (e.memoizedProps !== t.pendingProps) ic = !0;
		else {
			if (!jc(e, n) && !(t.flags & 128)) return ic = !1, Mc(e, t, n);
			ic = !!(e.flags & 131072);
		}
		else ic = !1, z && t.flags & 1048576 && Ai(t, Ci, t.index);
		switch (t.lanes = 0, t.tag) {
			case 16:
				a: {
					var r = t.pendingProps;
					if (e = Oa(t.elementType), t.type = e, typeof e == "function") ui(e) ? (r = qs(e, r), t.tag = 1, t = vc(null, t, e, r, n)) : (t.tag = 0, t = gc(null, t, e, r, n));
					else {
						if (e != null) {
							var i = e.$$typeof;
							if (i === w) {
								t.tag = 11, t = oc(null, t, e, r, n);
								break a;
							} else if (i === te) {
								t.tag = 14, t = sc(null, t, e, r, n);
								break a;
							}
						}
						throw t = oe(e) || e, Error(a(306, t, ""));
					}
				}
				return t;
			case 0: return gc(e, t, t.type, t.pendingProps, n);
			case 1: return r = t.type, i = qs(r, t.pendingProps), vc(e, t, r, i, n);
			case 3:
				a: {
					if (ge(t, t.stateNode.containerInfo), e === null) throw Error(a(387));
					r = t.pendingProps;
					var o = t.memoizedState;
					i = o.element, Ha(e, t), Ya(t, r, null, n);
					var s = t.memoizedState;
					if (r = s.cache, Ji(t, sa, r), r !== o.cache && Zi(t, [sa], n, !0), Ja(), r = s.element, o.isDehydrated) if (o = {
						element: r,
						isDehydrated: !1,
						cache: s.cache
					}, t.updateQueue.baseState = o, t.memoizedState = o, t.flags & 256) {
						t = yc(e, t, r, n);
						break a;
					} else if (r !== i) {
						i = yi(Error(a(424)), t), Wi(i), t = yc(e, t, r, n);
						break a;
					} else {
						switch (e = t.stateNode.containerInfo, e.nodeType) {
							case 9:
								e = e.body;
								break;
							default: e = e.nodeName === "HTML" ? e.ownerDocument.body : e;
						}
						for (R = cf(e.firstChild), Pi = t, z = !0, Fi = null, Ii = !0, n = za(t, null, r, n), t.child = n; n;) n.flags = n.flags & -3 | 4096, n = n.sibling;
					}
					else {
						if (Hi(), r === i) {
							t = Ac(e, t, n);
							break a;
						}
						ac(e, t, r, n);
					}
					t = t.child;
				}
				return t;
			case 26: return hc(e, t), e === null ? (n = kf(t.type, null, t.pendingProps, null)) ? t.memoizedState = n : z || (n = t.type, e = t.pendingProps, r = Bd(me.current).createElement(n), r[ft] = t, r[pt] = e, Pd(r, n, e), Ct(r), t.stateNode = r) : t.memoizedState = kf(t.type, e.memoizedProps, t.pendingProps, e.memoizedState), null;
			case 27: return ve(t), e === null && z && (r = t.stateNode = ff(t.type, t.pendingProps, me.current), Pi = t, Ii = !0, i = R, Zd(t.type) ? (lf = i, R = cf(r.firstChild)) : R = i), ac(e, t, t.pendingProps.children, n), hc(e, t), e === null && (t.flags |= 4194304), t.child;
			case 5: return e === null && z && ((i = r = R) && (r = tf(r, t.type, t.pendingProps, Ii), r === null ? i = !1 : (t.stateNode = r, Pi = t, R = cf(r.firstChild), Ii = !1, i = !0)), i || Ri(t)), ve(t), i = t.type, o = t.pendingProps, s = e === null ? null : e.memoizedProps, r = o.children, Ud(i, o) ? r = null : s !== null && Ud(i, s) && (t.flags |= 32), t.memoizedState !== null && (i = Co(e, t, Eo, null, null, n), Qf._currentValue = i), hc(e, t), ac(e, t, r, n), t.child;
			case 6: return e === null && z && ((e = n = R) && (n = nf(n, t.pendingProps, Ii), n === null ? e = !1 : (t.stateNode = n, Pi = t, R = null, e = !0)), e || Ri(t)), null;
			case 13: return Cc(e, t, n);
			case 4: return ge(t, t.stateNode.containerInfo), r = t.pendingProps, e === null ? t.child = Ra(t, null, r, n) : ac(e, t, r, n), t.child;
			case 11: return oc(e, t, t.type, t.pendingProps, n);
			case 7: return ac(e, t, t.pendingProps, n), t.child;
			case 8: return ac(e, t, t.pendingProps.children, n), t.child;
			case 12: return ac(e, t, t.pendingProps.children, n), t.child;
			case 10: return r = t.pendingProps, Ji(t, t.type, r.value), ac(e, t, r.children, n), t.child;
			case 9: return i = t.type._context, r = t.pendingProps.children, ea(t), i = ta(i), r = r(i), t.flags |= 1, ac(e, t, r, n), t.child;
			case 14: return sc(e, t, t.type, t.pendingProps, n);
			case 15: return cc(e, t, t.type, t.pendingProps, n);
			case 19: return kc(e, t, n);
			case 31: return mc(e, t, n);
			case 22: return lc(e, t, n, t.pendingProps);
			case 24: return ea(t), r = ta(sa), e === null ? (i = ya(), i === null && (i = K, o = ca(), i.pooledCache = o, o.refCount++, o !== null && (i.pooledCacheLanes |= n), i = o), t.memoizedState = {
				parent: r,
				cache: i
			}, Va(t), Ji(t, sa, i)) : ((e.lanes & n) !== 0 && (Ha(e, t), Ya(t, null, null, n), Ja()), i = e.memoizedState, o = t.memoizedState, i.parent === r ? (r = o.cache, Ji(t, sa, r), r !== i.cache && Zi(t, [sa], n, !0)) : (i = {
				parent: r,
				cache: r
			}, t.memoizedState = i, t.lanes === 0 && (t.memoizedState = t.updateQueue.baseState = i), Ji(t, sa, r))), ac(e, t, t.pendingProps.children, n), t.child;
			case 29: throw t.pendingProps;
		}
		throw Error(a(156, t.tag));
	}
	function Pc(e) {
		e.flags |= 4;
	}
	function Fc(e, t, n, r, i) {
		if ((t = (e.mode & 32) != 0) && (t = !1), t) {
			if (e.flags |= 16777216, (i & 335544128) === i) if (e.stateNode.complete) e.flags |= 8192;
			else if (wu()) e.flags |= 8192;
			else throw ka = Ta, Ca;
		} else e.flags &= -16777217;
	}
	function Ic(e, t) {
		if (t.type !== "stylesheet" || t.state.loading & 4) e.flags &= -16777217;
		else if (e.flags |= 16777216, !Wf(t)) if (wu()) e.flags |= 8192;
		else throw ka = Ta, Ca;
	}
	function Lc(e, t) {
		t !== null && (e.flags |= 4), e.flags & 16384 && (t = e.tag === 22 ? 536870912 : et(), e.lanes |= t, Yl |= t);
	}
	function Rc(e, t) {
		if (!z) switch (e.tailMode) {
			case "hidden":
				t = e.tail;
				for (var n = null; t !== null;) t.alternate !== null && (n = t), t = t.sibling;
				n === null ? e.tail = null : n.sibling = null;
				break;
			case "collapsed":
				n = e.tail;
				for (var r = null; n !== null;) n.alternate !== null && (r = n), n = n.sibling;
				r === null ? t || e.tail === null ? e.tail = null : e.tail.sibling = null : r.sibling = null;
		}
	}
	function U(e) {
		var t = e.alternate !== null && e.alternate.child === e.child, n = 0, r = 0;
		if (t) for (var i = e.child; i !== null;) n |= i.lanes | i.childLanes, r |= i.subtreeFlags & 65011712, r |= i.flags & 65011712, i.return = e, i = i.sibling;
		else for (i = e.child; i !== null;) n |= i.lanes | i.childLanes, r |= i.subtreeFlags, r |= i.flags, i.return = e, i = i.sibling;
		return e.subtreeFlags |= r, e.childLanes = n, t;
	}
	function zc(e, t, n) {
		var r = t.pendingProps;
		switch (Mi(t), t.tag) {
			case 16:
			case 15:
			case 0:
			case 11:
			case 7:
			case 8:
			case 12:
			case 9:
			case 14: return U(t), null;
			case 1: return U(t), null;
			case 3: return n = t.stateNode, r = null, e !== null && (r = e.memoizedState.cache), t.memoizedState.cache !== r && (t.flags |= 2048), Yi(sa), _e(), n.pendingContext && (n.context = n.pendingContext, n.pendingContext = null), (e === null || e.child === null) && (Vi(t) ? Pc(t) : e === null || e.memoizedState.isDehydrated && !(t.flags & 256) || (t.flags |= 1024, Ui())), U(t), null;
			case 26:
				var i = t.type, o = t.memoizedState;
				return e === null ? (Pc(t), o === null ? (U(t), Fc(t, i, null, r, n)) : (U(t), Ic(t, o))) : o ? o === e.memoizedState ? (U(t), t.flags &= -16777217) : (Pc(t), U(t), Ic(t, o)) : (e = e.memoizedProps, e !== r && Pc(t), U(t), Fc(t, i, e, r, n)), null;
			case 27:
				if (ye(t), n = me.current, i = t.type, e !== null && t.stateNode != null) e.memoizedProps !== r && Pc(t);
				else {
					if (!r) {
						if (t.stateNode === null) throw Error(a(166));
						return U(t), null;
					}
					e = fe.current, Vi(t) ? zi(t, e) : (e = ff(i, r, n), t.stateNode = e, Pc(t));
				}
				return U(t), null;
			case 5:
				if (ye(t), i = t.type, e !== null && t.stateNode != null) e.memoizedProps !== r && Pc(t);
				else {
					if (!r) {
						if (t.stateNode === null) throw Error(a(166));
						return U(t), null;
					}
					if (o = fe.current, Vi(t)) zi(t, o);
					else {
						var s = Bd(me.current);
						switch (o) {
							case 1:
								o = s.createElementNS("http://www.w3.org/2000/svg", i);
								break;
							case 2:
								o = s.createElementNS("http://www.w3.org/1998/Math/MathML", i);
								break;
							default: switch (i) {
								case "svg":
									o = s.createElementNS("http://www.w3.org/2000/svg", i);
									break;
								case "math":
									o = s.createElementNS("http://www.w3.org/1998/Math/MathML", i);
									break;
								case "script":
									o = s.createElement("div"), o.innerHTML = "<script><\/script>", o = o.removeChild(o.firstChild);
									break;
								case "select":
									o = typeof r.is == "string" ? s.createElement("select", { is: r.is }) : s.createElement("select"), r.multiple ? o.multiple = !0 : r.size && (o.size = r.size);
									break;
								default: o = typeof r.is == "string" ? s.createElement(i, { is: r.is }) : s.createElement(i);
							}
						}
						o[ft] = t, o[pt] = r;
						a: for (s = t.child; s !== null;) {
							if (s.tag === 5 || s.tag === 6) o.appendChild(s.stateNode);
							else if (s.tag !== 4 && s.tag !== 27 && s.child !== null) {
								s.child.return = s, s = s.child;
								continue;
							}
							if (s === t) break a;
							for (; s.sibling === null;) {
								if (s.return === null || s.return === t) break a;
								s = s.return;
							}
							s.sibling.return = s.return, s = s.sibling;
						}
						t.stateNode = o;
						a: switch (Pd(o, i, r), i) {
							case "button":
							case "input":
							case "select":
							case "textarea":
								r = !!r.autoFocus;
								break a;
							case "img":
								r = !0;
								break a;
							default: r = !1;
						}
						r && Pc(t);
					}
				}
				return U(t), Fc(t, t.type, e === null ? null : e.memoizedProps, t.pendingProps, n), null;
			case 6:
				if (e && t.stateNode != null) e.memoizedProps !== r && Pc(t);
				else {
					if (typeof r != "string" && t.stateNode === null) throw Error(a(166));
					if (e = me.current, Vi(t)) {
						if (e = t.stateNode, n = t.memoizedProps, r = null, i = Pi, i !== null) switch (i.tag) {
							case 27:
							case 5: r = i.memoizedProps;
						}
						e[ft] = t, e = !!(e.nodeValue === n || r !== null && !0 === r.suppressHydrationWarning || Md(e.nodeValue, n)), e || Ri(t, !0);
					} else e = Bd(e).createTextNode(r), e[ft] = t, t.stateNode = e;
				}
				return U(t), null;
			case 31:
				if (n = t.memoizedState, e === null || e.memoizedState !== null) {
					if (r = Vi(t), n !== null) {
						if (e === null) {
							if (!r) throw Error(a(318));
							if (e = t.memoizedState, e = e === null ? null : e.dehydrated, !e) throw Error(a(557));
							e[ft] = t;
						} else Hi(), !(t.flags & 128) && (t.memoizedState = null), t.flags |= 4;
						U(t), e = !1;
					} else n = Ui(), e !== null && e.memoizedState !== null && (e.memoizedState.hydrationErrors = n), e = !0;
					if (!e) return t.flags & 256 ? (lo(t), t) : (lo(t), null);
					if (t.flags & 128) throw Error(a(558));
				}
				return U(t), null;
			case 13:
				if (r = t.memoizedState, e === null || e.memoizedState !== null && e.memoizedState.dehydrated !== null) {
					if (i = Vi(t), r !== null && r.dehydrated !== null) {
						if (e === null) {
							if (!i) throw Error(a(318));
							if (i = t.memoizedState, i = i === null ? null : i.dehydrated, !i) throw Error(a(317));
							i[ft] = t;
						} else Hi(), !(t.flags & 128) && (t.memoizedState = null), t.flags |= 4;
						U(t), i = !1;
					} else i = Ui(), e !== null && e.memoizedState !== null && (e.memoizedState.hydrationErrors = i), i = !0;
					if (!i) return t.flags & 256 ? (lo(t), t) : (lo(t), null);
				}
				return lo(t), t.flags & 128 ? (t.lanes = n, t) : (n = r !== null, e = e !== null && e.memoizedState !== null, n && (r = t.child, i = null, r.alternate !== null && r.alternate.memoizedState !== null && r.alternate.memoizedState.cachePool !== null && (i = r.alternate.memoizedState.cachePool.pool), o = null, r.memoizedState !== null && r.memoizedState.cachePool !== null && (o = r.memoizedState.cachePool.pool), o !== i && (r.flags |= 2048)), n !== e && n && (t.child.flags |= 8192), Lc(t, t.updateQueue), U(t), null);
			case 4: return _e(), e === null && Sd(t.stateNode.containerInfo), U(t), null;
			case 10: return Yi(t.type), U(t), null;
			case 19:
				if (A(uo), r = t.memoizedState, r === null) return U(t), null;
				if (i = (t.flags & 128) != 0, o = r.rendering, o === null) if (i) Rc(r, !1);
				else {
					if (X !== 0 || e !== null && e.flags & 128) for (e = t.child; e !== null;) {
						if (o = fo(e), o !== null) {
							for (t.flags |= 128, Rc(r, !1), e = o.updateQueue, t.updateQueue = e, Lc(t, e), t.subtreeFlags = 0, e = n, n = t.child; n !== null;) fi(n, e), n = n.sibling;
							return j(uo, uo.current & 1 | 2), z && ki(t, r.treeForkCount), t.child;
						}
						e = e.sibling;
					}
					r.tail !== null && je() > tu && (t.flags |= 128, i = !0, Rc(r, !1), t.lanes = 4194304);
				}
				else {
					if (!i) if (e = fo(o), e !== null) {
						if (t.flags |= 128, i = !0, e = e.updateQueue, t.updateQueue = e, Lc(t, e), Rc(r, !0), r.tail === null && r.tailMode === "hidden" && !o.alternate && !z) return U(t), null;
					} else 2 * je() - r.renderingStartTime > tu && n !== 536870912 && (t.flags |= 128, i = !0, Rc(r, !1), t.lanes = 4194304);
					r.isBackwards ? (o.sibling = t.child, t.child = o) : (e = r.last, e === null ? t.child = o : e.sibling = o, r.last = o);
				}
				return r.tail === null ? (U(t), null) : (e = r.tail, r.rendering = e, r.tail = e.sibling, r.renderingStartTime = je(), e.sibling = null, n = uo.current, j(uo, i ? n & 1 | 2 : n & 1), z && ki(t, r.treeForkCount), e);
			case 22:
			case 23: return lo(t), no(), r = t.memoizedState !== null, e === null ? r && (t.flags |= 8192) : e.memoizedState !== null !== r && (t.flags |= 8192), r ? n & 536870912 && !(t.flags & 128) && (U(t), t.subtreeFlags & 6 && (t.flags |= 8192)) : U(t), n = t.updateQueue, n !== null && Lc(t, n.retryQueue), n = null, e !== null && e.memoizedState !== null && e.memoizedState.cachePool !== null && (n = e.memoizedState.cachePool.pool), r = null, t.memoizedState !== null && t.memoizedState.cachePool !== null && (r = t.memoizedState.cachePool.pool), r !== n && (t.flags |= 2048), e !== null && A(va), null;
			case 24: return n = null, e !== null && (n = e.memoizedState.cache), t.memoizedState.cache !== n && (t.flags |= 2048), Yi(sa), U(t), null;
			case 25: return null;
			case 30: return null;
		}
		throw Error(a(156, t.tag));
	}
	function Bc(e, t) {
		switch (Mi(t), t.tag) {
			case 1: return e = t.flags, e & 65536 ? (t.flags = e & -65537 | 128, t) : null;
			case 3: return Yi(sa), _e(), e = t.flags, e & 65536 && !(e & 128) ? (t.flags = e & -65537 | 128, t) : null;
			case 26:
			case 27:
			case 5: return ye(t), null;
			case 31:
				if (t.memoizedState !== null) {
					if (lo(t), t.alternate === null) throw Error(a(340));
					Hi();
				}
				return e = t.flags, e & 65536 ? (t.flags = e & -65537 | 128, t) : null;
			case 13:
				if (lo(t), e = t.memoizedState, e !== null && e.dehydrated !== null) {
					if (t.alternate === null) throw Error(a(340));
					Hi();
				}
				return e = t.flags, e & 65536 ? (t.flags = e & -65537 | 128, t) : null;
			case 19: return A(uo), null;
			case 4: return _e(), null;
			case 10: return Yi(t.type), null;
			case 22:
			case 23: return lo(t), no(), e !== null && A(va), e = t.flags, e & 65536 ? (t.flags = e & -65537 | 128, t) : null;
			case 24: return Yi(sa), null;
			case 25: return null;
			default: return null;
		}
	}
	function Vc(e, t) {
		switch (Mi(t), t.tag) {
			case 3:
				Yi(sa), _e();
				break;
			case 26:
			case 27:
			case 5:
				ye(t);
				break;
			case 4:
				_e();
				break;
			case 31:
				t.memoizedState !== null && lo(t);
				break;
			case 13:
				lo(t);
				break;
			case 19:
				A(uo);
				break;
			case 10:
				Yi(t.type);
				break;
			case 22:
			case 23:
				lo(t), no(), e !== null && A(va);
				break;
			case 24: Yi(sa);
		}
	}
	function Hc(e, t) {
		try {
			var n = t.updateQueue, r = n === null ? null : n.lastEffect;
			if (r !== null) {
				var i = r.next;
				n = i;
				do {
					if ((n.tag & e) === e) {
						r = void 0;
						var a = n.create, o = n.inst;
						r = a(), o.destroy = r;
					}
					n = n.next;
				} while (n !== i);
			}
		} catch (e) {
			Z(t, t.return, e);
		}
	}
	function Uc(e, t, n) {
		try {
			var r = t.updateQueue, i = r === null ? null : r.lastEffect;
			if (i !== null) {
				var a = i.next;
				r = a;
				do {
					if ((r.tag & e) === e) {
						var o = r.inst, s = o.destroy;
						if (s !== void 0) {
							o.destroy = void 0, i = t;
							var c = n, l = s;
							try {
								l();
							} catch (e) {
								Z(i, c, e);
							}
						}
					}
					r = r.next;
				} while (r !== a);
			}
		} catch (e) {
			Z(t, t.return, e);
		}
	}
	function Wc(e) {
		var t = e.updateQueue;
		if (t !== null) {
			var n = e.stateNode;
			try {
				Za(t, n);
			} catch (t) {
				Z(e, e.return, t);
			}
		}
	}
	function Gc(e, t, n) {
		n.props = qs(e.type, e.memoizedProps), n.state = e.memoizedState;
		try {
			n.componentWillUnmount();
		} catch (n) {
			Z(e, t, n);
		}
	}
	function Kc(e, t) {
		try {
			var n = e.ref;
			if (n !== null) {
				switch (e.tag) {
					case 26:
					case 27:
					case 5:
						var r = e.stateNode;
						break;
					case 30:
						r = e.stateNode;
						break;
					default: r = e.stateNode;
				}
				typeof n == "function" ? e.refCleanup = n(r) : n.current = r;
			}
		} catch (n) {
			Z(e, t, n);
		}
	}
	function qc(e, t) {
		var n = e.ref, r = e.refCleanup;
		if (n !== null) if (typeof r == "function") try {
			r();
		} catch (n) {
			Z(e, t, n);
		} finally {
			e.refCleanup = null, e = e.alternate, e != null && (e.refCleanup = null);
		}
		else if (typeof n == "function") try {
			n(null);
		} catch (n) {
			Z(e, t, n);
		}
		else n.current = null;
	}
	function Jc(e) {
		var t = e.type, n = e.memoizedProps, r = e.stateNode;
		try {
			a: switch (t) {
				case "button":
				case "input":
				case "select":
				case "textarea":
					n.autoFocus && r.focus();
					break a;
				case "img": n.src ? r.src = n.src : n.srcSet && (r.srcset = n.srcSet);
			}
		} catch (t) {
			Z(e, e.return, t);
		}
	}
	function Yc(e, t, n) {
		try {
			var r = e.stateNode;
			Fd(r, e.type, n, t), r[pt] = t;
		} catch (t) {
			Z(e, e.return, t);
		}
	}
	function Xc(e) {
		return e.tag === 5 || e.tag === 3 || e.tag === 26 || e.tag === 27 && Zd(e.type) || e.tag === 4;
	}
	function Zc(e) {
		a: for (;;) {
			for (; e.sibling === null;) {
				if (e.return === null || Xc(e.return)) return null;
				e = e.return;
			}
			for (e.sibling.return = e.return, e = e.sibling; e.tag !== 5 && e.tag !== 6 && e.tag !== 18;) {
				if (e.tag === 27 && Zd(e.type) || e.flags & 2 || e.child === null || e.tag === 4) continue a;
				e.child.return = e, e = e.child;
			}
			if (!(e.flags & 2)) return e.stateNode;
		}
	}
	function Qc(e, t, n) {
		var r = e.tag;
		if (r === 5 || r === 6) e = e.stateNode, t ? (n.nodeType === 9 ? n.body : n.nodeName === "HTML" ? n.ownerDocument.body : n).insertBefore(e, t) : (t = n.nodeType === 9 ? n.body : n.nodeName === "HTML" ? n.ownerDocument.body : n, t.appendChild(e), n = n._reactRootContainer, n != null || t.onclick !== null || (t.onclick = F));
		else if (r !== 4 && (r === 27 && Zd(e.type) && (n = e.stateNode, t = null), e = e.child, e !== null)) for (Qc(e, t, n), e = e.sibling; e !== null;) Qc(e, t, n), e = e.sibling;
	}
	function $c(e, t, n) {
		var r = e.tag;
		if (r === 5 || r === 6) e = e.stateNode, t ? n.insertBefore(e, t) : n.appendChild(e);
		else if (r !== 4 && (r === 27 && Zd(e.type) && (n = e.stateNode), e = e.child, e !== null)) for ($c(e, t, n), e = e.sibling; e !== null;) $c(e, t, n), e = e.sibling;
	}
	function el(e) {
		var t = e.stateNode, n = e.memoizedProps;
		try {
			for (var r = e.type, i = t.attributes; i.length;) t.removeAttributeNode(i[0]);
			Pd(t, r, n), t[ft] = e, t[pt] = n;
		} catch (t) {
			Z(e, e.return, t);
		}
	}
	var tl = !1, nl = !1, rl = !1, il = typeof WeakSet == "function" ? WeakSet : Set, al = null;
	function ol(e, t) {
		if (e = e.containerInfo, Rd = sp, e = Or(e), kr(e)) {
			if ("selectionStart" in e) var n = {
				start: e.selectionStart,
				end: e.selectionEnd
			};
			else a: {
				n = (n = e.ownerDocument) && n.defaultView || window;
				var r = n.getSelection && n.getSelection();
				if (r && r.rangeCount !== 0) {
					n = r.anchorNode;
					var i = r.anchorOffset, o = r.focusNode;
					r = r.focusOffset;
					try {
						n.nodeType, o.nodeType;
					} catch {
						n = null;
						break a;
					}
					var s = 0, c = -1, l = -1, u = 0, d = 0, f = e, p = null;
					b: for (;;) {
						for (var m; f !== n || i !== 0 && f.nodeType !== 3 || (c = s + i), f !== o || r !== 0 && f.nodeType !== 3 || (l = s + r), f.nodeType === 3 && (s += f.nodeValue.length), (m = f.firstChild) !== null;) p = f, f = m;
						for (;;) {
							if (f === e) break b;
							if (p === n && ++u === i && (c = s), p === o && ++d === r && (l = s), (m = f.nextSibling) !== null) break;
							f = p, p = f.parentNode;
						}
						f = m;
					}
					n = c === -1 || l === -1 ? null : {
						start: c,
						end: l
					};
				} else n = null;
			}
			n ||= {
				start: 0,
				end: 0
			};
		} else n = null;
		for (zd = {
			focusedElem: e,
			selectionRange: n
		}, sp = !1, al = t; al !== null;) if (t = al, e = t.child, t.subtreeFlags & 1028 && e !== null) e.return = t, al = e;
		else for (; al !== null;) {
			switch (t = al, o = t.alternate, e = t.flags, t.tag) {
				case 0:
					if (e & 4 && (e = t.updateQueue, e = e === null ? null : e.events, e !== null)) for (n = 0; n < e.length; n++) i = e[n], i.ref.impl = i.nextImpl;
					break;
				case 11:
				case 15: break;
				case 1:
					if (e & 1024 && o !== null) {
						e = void 0, n = t, i = o.memoizedProps, o = o.memoizedState, r = n.stateNode;
						try {
							var h = qs(n.type, i);
							e = r.getSnapshotBeforeUpdate(h, o), r.__reactInternalSnapshotBeforeUpdate = e;
						} catch (e) {
							Z(n, n.return, e);
						}
					}
					break;
				case 3:
					if (e & 1024) {
						if (e = t.stateNode.containerInfo, n = e.nodeType, n === 9) ef(e);
						else if (n === 1) switch (e.nodeName) {
							case "HEAD":
							case "HTML":
							case "BODY":
								ef(e);
								break;
							default: e.textContent = "";
						}
					}
					break;
				case 5:
				case 26:
				case 27:
				case 6:
				case 4:
				case 17: break;
				default: if (e & 1024) throw Error(a(163));
			}
			if (e = t.sibling, e !== null) {
				e.return = t.return, al = e;
				break;
			}
			al = t.return;
		}
	}
	function sl(e, t, n) {
		var r = n.flags;
		switch (n.tag) {
			case 0:
			case 11:
			case 15:
				xl(e, n), r & 4 && Hc(5, n);
				break;
			case 1:
				if (xl(e, n), r & 4) if (e = n.stateNode, t === null) try {
					e.componentDidMount();
				} catch (e) {
					Z(n, n.return, e);
				}
				else {
					var i = qs(n.type, t.memoizedProps);
					t = t.memoizedState;
					try {
						e.componentDidUpdate(i, t, e.__reactInternalSnapshotBeforeUpdate);
					} catch (e) {
						Z(n, n.return, e);
					}
				}
				r & 64 && Wc(n), r & 512 && Kc(n, n.return);
				break;
			case 3:
				if (xl(e, n), r & 64 && (e = n.updateQueue, e !== null)) {
					if (t = null, n.child !== null) switch (n.child.tag) {
						case 27:
						case 5:
							t = n.child.stateNode;
							break;
						case 1: t = n.child.stateNode;
					}
					try {
						Za(e, t);
					} catch (e) {
						Z(n, n.return, e);
					}
				}
				break;
			case 27: t === null && r & 4 && el(n);
			case 26:
			case 5:
				xl(e, n), t === null && r & 4 && Jc(n), r & 512 && Kc(n, n.return);
				break;
			case 12:
				xl(e, n);
				break;
			case 31:
				xl(e, n), r & 4 && fl(e, n);
				break;
			case 13:
				xl(e, n), r & 4 && pl(e, n), r & 64 && (e = n.memoizedState, e !== null && (e = e.dehydrated, e !== null && (n = Ju.bind(null, n), sf(e, n))));
				break;
			case 22:
				if (r = n.memoizedState !== null || tl, !r) {
					t = t !== null && t.memoizedState !== null || nl, i = tl;
					var a = nl;
					tl = r, (nl = t) && !a ? Cl(e, n, (n.subtreeFlags & 8772) != 0) : xl(e, n), tl = i, nl = a;
				}
				break;
			case 30: break;
			default: xl(e, n);
		}
	}
	function cl(e) {
		var t = e.alternate;
		t !== null && (e.alternate = null, cl(t)), e.child = null, e.deletions = null, e.sibling = null, e.tag === 5 && (t = e.stateNode, t !== null && bt(t)), e.stateNode = null, e.return = null, e.dependencies = null, e.memoizedProps = null, e.memoizedState = null, e.pendingProps = null, e.stateNode = null, e.updateQueue = null;
	}
	var W = null, ll = !1;
	function ul(e, t, n) {
		for (n = n.child; n !== null;) dl(e, t, n), n = n.sibling;
	}
	function dl(e, t, n) {
		if (Ve && typeof Ve.onCommitFiberUnmount == "function") try {
			Ve.onCommitFiberUnmount(Be, n);
		} catch {}
		switch (n.tag) {
			case 26:
				nl || qc(n, t), ul(e, t, n), n.memoizedState ? n.memoizedState.count-- : n.stateNode && (n = n.stateNode, n.parentNode.removeChild(n));
				break;
			case 27:
				nl || qc(n, t);
				var r = W, i = ll;
				Zd(n.type) && (W = n.stateNode, ll = !1), ul(e, t, n), pf(n.stateNode), W = r, ll = i;
				break;
			case 5: nl || qc(n, t);
			case 6:
				if (r = W, i = ll, W = null, ul(e, t, n), W = r, ll = i, W !== null) if (ll) try {
					(W.nodeType === 9 ? W.body : W.nodeName === "HTML" ? W.ownerDocument.body : W).removeChild(n.stateNode);
				} catch (e) {
					Z(n, t, e);
				}
				else try {
					W.removeChild(n.stateNode);
				} catch (e) {
					Z(n, t, e);
				}
				break;
			case 18:
				W !== null && (ll ? (e = W, Qd(e.nodeType === 9 ? e.body : e.nodeName === "HTML" ? e.ownerDocument.body : e, n.stateNode), Np(e)) : Qd(W, n.stateNode));
				break;
			case 4:
				r = W, i = ll, W = n.stateNode.containerInfo, ll = !0, ul(e, t, n), W = r, ll = i;
				break;
			case 0:
			case 11:
			case 14:
			case 15:
				Uc(2, n, t), nl || Uc(4, n, t), ul(e, t, n);
				break;
			case 1:
				nl || (qc(n, t), r = n.stateNode, typeof r.componentWillUnmount == "function" && Gc(n, t, r)), ul(e, t, n);
				break;
			case 21:
				ul(e, t, n);
				break;
			case 22:
				nl = (r = nl) || n.memoizedState !== null, ul(e, t, n), nl = r;
				break;
			default: ul(e, t, n);
		}
	}
	function fl(e, t) {
		if (t.memoizedState === null && (e = t.alternate, e !== null && (e = e.memoizedState, e !== null))) {
			e = e.dehydrated;
			try {
				Np(e);
			} catch (e) {
				Z(t, t.return, e);
			}
		}
	}
	function pl(e, t) {
		if (t.memoizedState === null && (e = t.alternate, e !== null && (e = e.memoizedState, e !== null && (e = e.dehydrated, e !== null)))) try {
			Np(e);
		} catch (e) {
			Z(t, t.return, e);
		}
	}
	function ml(e) {
		switch (e.tag) {
			case 31:
			case 13:
			case 19:
				var t = e.stateNode;
				return t === null && (t = e.stateNode = new il()), t;
			case 22: return e = e.stateNode, t = e._retryCache, t === null && (t = e._retryCache = new il()), t;
			default: throw Error(a(435, e.tag));
		}
	}
	function hl(e, t) {
		var n = ml(e);
		t.forEach(function(t) {
			if (!n.has(t)) {
				n.add(t);
				var r = Yu.bind(null, e, t);
				t.then(r, r);
			}
		});
	}
	function gl(e, t) {
		var n = t.deletions;
		if (n !== null) for (var r = 0; r < n.length; r++) {
			var i = n[r], o = e, s = t, c = s;
			a: for (; c !== null;) {
				switch (c.tag) {
					case 27:
						if (Zd(c.type)) {
							W = c.stateNode, ll = !1;
							break a;
						}
						break;
					case 5:
						W = c.stateNode, ll = !1;
						break a;
					case 3:
					case 4:
						W = c.stateNode.containerInfo, ll = !0;
						break a;
				}
				c = c.return;
			}
			if (W === null) throw Error(a(160));
			dl(o, s, i), W = null, ll = !1, o = i.alternate, o !== null && (o.return = null), i.return = null;
		}
		if (t.subtreeFlags & 13886) for (t = t.child; t !== null;) vl(t, e), t = t.sibling;
	}
	var _l = null;
	function vl(e, t) {
		var n = e.alternate, r = e.flags;
		switch (e.tag) {
			case 0:
			case 11:
			case 14:
			case 15:
				gl(t, e), yl(e), r & 4 && (Uc(3, e, e.return), Hc(3, e), Uc(5, e, e.return));
				break;
			case 1:
				gl(t, e), yl(e), r & 512 && (nl || n === null || qc(n, n.return)), r & 64 && tl && (e = e.updateQueue, e !== null && (r = e.callbacks, r !== null && (n = e.shared.hiddenCallbacks, e.shared.hiddenCallbacks = n === null ? r : n.concat(r))));
				break;
			case 26:
				var i = _l;
				if (gl(t, e), yl(e), r & 512 && (nl || n === null || qc(n, n.return)), r & 4) {
					var o = n === null ? null : n.memoizedState;
					if (r = e.memoizedState, n === null) if (r === null) if (e.stateNode === null) {
						a: {
							r = e.type, n = e.memoizedProps, i = i.ownerDocument || i;
							b: switch (r) {
								case "title":
									o = i.getElementsByTagName("title")[0], (!o || o[yt] || o[ft] || o.namespaceURI === "http://www.w3.org/2000/svg" || o.hasAttribute("itemprop")) && (o = i.createElement(r), i.head.insertBefore(o, i.querySelector("head > title"))), Pd(o, r, n), o[ft] = e, Ct(o), r = o;
									break a;
								case "link":
									var s = Vf("link", "href", i).get(r + (n.href || ""));
									if (s) {
										for (var c = 0; c < s.length; c++) if (o = s[c], o.getAttribute("href") === (n.href == null || n.href === "" ? null : n.href) && o.getAttribute("rel") === (n.rel == null ? null : n.rel) && o.getAttribute("title") === (n.title == null ? null : n.title) && o.getAttribute("crossorigin") === (n.crossOrigin == null ? null : n.crossOrigin)) {
											s.splice(c, 1);
											break b;
										}
									}
									o = i.createElement(r), Pd(o, r, n), i.head.appendChild(o);
									break;
								case "meta":
									if (s = Vf("meta", "content", i).get(r + (n.content || ""))) {
										for (c = 0; c < s.length; c++) if (o = s[c], o.getAttribute("content") === (n.content == null ? null : "" + n.content) && o.getAttribute("name") === (n.name == null ? null : n.name) && o.getAttribute("property") === (n.property == null ? null : n.property) && o.getAttribute("http-equiv") === (n.httpEquiv == null ? null : n.httpEquiv) && o.getAttribute("charset") === (n.charSet == null ? null : n.charSet)) {
											s.splice(c, 1);
											break b;
										}
									}
									o = i.createElement(r), Pd(o, r, n), i.head.appendChild(o);
									break;
								default: throw Error(a(468, r));
							}
							o[ft] = e, Ct(o), r = o;
						}
						e.stateNode = r;
					} else Hf(i, e.type, e.stateNode);
					else e.stateNode = If(i, r, e.memoizedProps);
					else o === r ? r === null && e.stateNode !== null && Yc(e, e.memoizedProps, n.memoizedProps) : (o === null ? n.stateNode !== null && (n = n.stateNode, n.parentNode.removeChild(n)) : o.count--, r === null ? Hf(i, e.type, e.stateNode) : If(i, r, e.memoizedProps));
				}
				break;
			case 27:
				gl(t, e), yl(e), r & 512 && (nl || n === null || qc(n, n.return)), n !== null && r & 4 && Yc(e, e.memoizedProps, n.memoizedProps);
				break;
			case 5:
				if (gl(t, e), yl(e), r & 512 && (nl || n === null || qc(n, n.return)), e.flags & 32) {
					i = e.stateNode;
					try {
						Yt(i, "");
					} catch (t) {
						Z(e, e.return, t);
					}
				}
				r & 4 && e.stateNode != null && (i = e.memoizedProps, Yc(e, i, n === null ? i : n.memoizedProps)), r & 1024 && (rl = !0);
				break;
			case 6:
				if (gl(t, e), yl(e), r & 4) {
					if (e.stateNode === null) throw Error(a(162));
					r = e.memoizedProps, n = e.stateNode;
					try {
						n.nodeValue = r;
					} catch (t) {
						Z(e, e.return, t);
					}
				}
				break;
			case 3:
				if (Bf = null, i = _l, _l = gf(t.containerInfo), gl(t, e), _l = i, yl(e), r & 4 && n !== null && n.memoizedState.isDehydrated) try {
					Np(t.containerInfo);
				} catch (t) {
					Z(e, e.return, t);
				}
				rl && (rl = !1, bl(e));
				break;
			case 4:
				r = _l, _l = gf(e.stateNode.containerInfo), gl(t, e), yl(e), _l = r;
				break;
			case 12:
				gl(t, e), yl(e);
				break;
			case 31:
				gl(t, e), yl(e), r & 4 && (r = e.updateQueue, r !== null && (e.updateQueue = null, hl(e, r)));
				break;
			case 13:
				gl(t, e), yl(e), e.child.flags & 8192 && e.memoizedState !== null != (n !== null && n.memoizedState !== null) && ($l = je()), r & 4 && (r = e.updateQueue, r !== null && (e.updateQueue = null, hl(e, r)));
				break;
			case 22:
				i = e.memoizedState !== null;
				var l = n !== null && n.memoizedState !== null, u = tl, d = nl;
				if (tl = u || i, nl = d || l, gl(t, e), nl = d, tl = u, yl(e), r & 8192) a: for (t = e.stateNode, t._visibility = i ? t._visibility & -2 : t._visibility | 1, i && (n === null || l || tl || nl || Sl(e)), n = null, t = e;;) {
					if (t.tag === 5 || t.tag === 26) {
						if (n === null) {
							l = n = t;
							try {
								if (o = l.stateNode, i) s = o.style, typeof s.setProperty == "function" ? s.setProperty("display", "none", "important") : s.display = "none";
								else {
									c = l.stateNode;
									var f = l.memoizedProps.style, p = f != null && f.hasOwnProperty("display") ? f.display : null;
									c.style.display = p == null || typeof p == "boolean" ? "" : ("" + p).trim();
								}
							} catch (e) {
								Z(l, l.return, e);
							}
						}
					} else if (t.tag === 6) {
						if (n === null) {
							l = t;
							try {
								l.stateNode.nodeValue = i ? "" : l.memoizedProps;
							} catch (e) {
								Z(l, l.return, e);
							}
						}
					} else if (t.tag === 18) {
						if (n === null) {
							l = t;
							try {
								var m = l.stateNode;
								i ? $d(m, !0) : $d(l.stateNode, !1);
							} catch (e) {
								Z(l, l.return, e);
							}
						}
					} else if ((t.tag !== 22 && t.tag !== 23 || t.memoizedState === null || t === e) && t.child !== null) {
						t.child.return = t, t = t.child;
						continue;
					}
					if (t === e) break a;
					for (; t.sibling === null;) {
						if (t.return === null || t.return === e) break a;
						n === t && (n = null), t = t.return;
					}
					n === t && (n = null), t.sibling.return = t.return, t = t.sibling;
				}
				r & 4 && (r = e.updateQueue, r !== null && (n = r.retryQueue, n !== null && (r.retryQueue = null, hl(e, n))));
				break;
			case 19:
				gl(t, e), yl(e), r & 4 && (r = e.updateQueue, r !== null && (e.updateQueue = null, hl(e, r)));
				break;
			case 30: break;
			case 21: break;
			default: gl(t, e), yl(e);
		}
	}
	function yl(e) {
		var t = e.flags;
		if (t & 2) {
			try {
				for (var n, r = e.return; r !== null;) {
					if (Xc(r)) {
						n = r;
						break;
					}
					r = r.return;
				}
				if (n == null) throw Error(a(160));
				switch (n.tag) {
					case 27:
						var i = n.stateNode;
						$c(e, Zc(e), i);
						break;
					case 5:
						var o = n.stateNode;
						n.flags & 32 && (Yt(o, ""), n.flags &= -33), $c(e, Zc(e), o);
						break;
					case 3:
					case 4:
						var s = n.stateNode.containerInfo;
						Qc(e, Zc(e), s);
						break;
					default: throw Error(a(161));
				}
			} catch (t) {
				Z(e, e.return, t);
			}
			e.flags &= -3;
		}
		t & 4096 && (e.flags &= -4097);
	}
	function bl(e) {
		if (e.subtreeFlags & 1024) for (e = e.child; e !== null;) {
			var t = e;
			bl(t), t.tag === 5 && t.flags & 1024 && t.stateNode.reset(), e = e.sibling;
		}
	}
	function xl(e, t) {
		if (t.subtreeFlags & 8772) for (t = t.child; t !== null;) sl(e, t.alternate, t), t = t.sibling;
	}
	function Sl(e) {
		for (e = e.child; e !== null;) {
			var t = e;
			switch (t.tag) {
				case 0:
				case 11:
				case 14:
				case 15:
					Uc(4, t, t.return), Sl(t);
					break;
				case 1:
					qc(t, t.return);
					var n = t.stateNode;
					typeof n.componentWillUnmount == "function" && Gc(t, t.return, n), Sl(t);
					break;
				case 27: pf(t.stateNode);
				case 26:
				case 5:
					qc(t, t.return), Sl(t);
					break;
				case 22:
					t.memoizedState === null && Sl(t);
					break;
				case 30:
					Sl(t);
					break;
				default: Sl(t);
			}
			e = e.sibling;
		}
	}
	function Cl(e, t, n) {
		for (n &&= (t.subtreeFlags & 8772) != 0, t = t.child; t !== null;) {
			var r = t.alternate, i = e, a = t, o = a.flags;
			switch (a.tag) {
				case 0:
				case 11:
				case 15:
					Cl(i, a, n), Hc(4, a);
					break;
				case 1:
					if (Cl(i, a, n), r = a, i = r.stateNode, typeof i.componentDidMount == "function") try {
						i.componentDidMount();
					} catch (e) {
						Z(r, r.return, e);
					}
					if (r = a, i = r.updateQueue, i !== null) {
						var s = r.stateNode;
						try {
							var c = i.shared.hiddenCallbacks;
							if (c !== null) for (i.shared.hiddenCallbacks = null, i = 0; i < c.length; i++) Xa(c[i], s);
						} catch (e) {
							Z(r, r.return, e);
						}
					}
					n && o & 64 && Wc(a), Kc(a, a.return);
					break;
				case 27: el(a);
				case 26:
				case 5:
					Cl(i, a, n), n && r === null && o & 4 && Jc(a), Kc(a, a.return);
					break;
				case 12:
					Cl(i, a, n);
					break;
				case 31:
					Cl(i, a, n), n && o & 4 && fl(i, a);
					break;
				case 13:
					Cl(i, a, n), n && o & 4 && pl(i, a);
					break;
				case 22:
					a.memoizedState === null && Cl(i, a, n), Kc(a, a.return);
					break;
				case 30: break;
				default: Cl(i, a, n);
			}
			t = t.sibling;
		}
	}
	function wl(e, t) {
		var n = null;
		e !== null && e.memoizedState !== null && e.memoizedState.cachePool !== null && (n = e.memoizedState.cachePool.pool), e = null, t.memoizedState !== null && t.memoizedState.cachePool !== null && (e = t.memoizedState.cachePool.pool), e !== n && (e != null && e.refCount++, n != null && la(n));
	}
	function Tl(e, t) {
		e = null, t.alternate !== null && (e = t.alternate.memoizedState.cache), t = t.memoizedState.cache, t !== e && (t.refCount++, e != null && la(e));
	}
	function El(e, t, n, r) {
		if (t.subtreeFlags & 10256) for (t = t.child; t !== null;) Dl(e, t, n, r), t = t.sibling;
	}
	function Dl(e, t, n, r) {
		var i = t.flags;
		switch (t.tag) {
			case 0:
			case 11:
			case 15:
				El(e, t, n, r), i & 2048 && Hc(9, t);
				break;
			case 1:
				El(e, t, n, r);
				break;
			case 3:
				El(e, t, n, r), i & 2048 && (e = null, t.alternate !== null && (e = t.alternate.memoizedState.cache), t = t.memoizedState.cache, t !== e && (t.refCount++, e != null && la(e)));
				break;
			case 12:
				if (i & 2048) {
					El(e, t, n, r), e = t.stateNode;
					try {
						var a = t.memoizedProps, o = a.id, s = a.onPostCommit;
						typeof s == "function" && s(o, t.alternate === null ? "mount" : "update", e.passiveEffectDuration, -0);
					} catch (e) {
						Z(t, t.return, e);
					}
				} else El(e, t, n, r);
				break;
			case 31:
				El(e, t, n, r);
				break;
			case 13:
				El(e, t, n, r);
				break;
			case 23: break;
			case 22:
				a = t.stateNode, o = t.alternate, t.memoizedState === null ? a._visibility & 2 ? El(e, t, n, r) : (a._visibility |= 2, Ol(e, t, n, r, (t.subtreeFlags & 10256) != 0 || !1)) : a._visibility & 2 ? El(e, t, n, r) : kl(e, t), i & 2048 && wl(o, t);
				break;
			case 24:
				El(e, t, n, r), i & 2048 && Tl(t.alternate, t);
				break;
			default: El(e, t, n, r);
		}
	}
	function Ol(e, t, n, r, i) {
		for (i &&= (t.subtreeFlags & 10256) != 0 || !1, t = t.child; t !== null;) {
			var a = e, o = t, s = n, c = r, l = o.flags;
			switch (o.tag) {
				case 0:
				case 11:
				case 15:
					Ol(a, o, s, c, i), Hc(8, o);
					break;
				case 23: break;
				case 22:
					var u = o.stateNode;
					o.memoizedState === null ? (u._visibility |= 2, Ol(a, o, s, c, i)) : u._visibility & 2 ? Ol(a, o, s, c, i) : kl(a, o), i && l & 2048 && wl(o.alternate, o);
					break;
				case 24:
					Ol(a, o, s, c, i), i && l & 2048 && Tl(o.alternate, o);
					break;
				default: Ol(a, o, s, c, i);
			}
			t = t.sibling;
		}
	}
	function kl(e, t) {
		if (t.subtreeFlags & 10256) for (t = t.child; t !== null;) {
			var n = e, r = t, i = r.flags;
			switch (r.tag) {
				case 22:
					kl(n, r), i & 2048 && wl(r.alternate, r);
					break;
				case 24:
					kl(n, r), i & 2048 && Tl(r.alternate, r);
					break;
				default: kl(n, r);
			}
			t = t.sibling;
		}
	}
	var Al = 8192;
	function jl(e, t, n) {
		if (e.subtreeFlags & Al) for (e = e.child; e !== null;) Ml(e, t, n), e = e.sibling;
	}
	function Ml(e, t, n) {
		switch (e.tag) {
			case 26:
				jl(e, t, n), e.flags & Al && e.memoizedState !== null && Gf(n, _l, e.memoizedState, e.memoizedProps);
				break;
			case 5:
				jl(e, t, n);
				break;
			case 3:
			case 4:
				var r = _l;
				_l = gf(e.stateNode.containerInfo), jl(e, t, n), _l = r;
				break;
			case 22:
				e.memoizedState === null && (r = e.alternate, r !== null && r.memoizedState !== null ? (r = Al, Al = 16777216, jl(e, t, n), Al = r) : jl(e, t, n));
				break;
			default: jl(e, t, n);
		}
	}
	function Nl(e) {
		var t = e.alternate;
		if (t !== null && (e = t.child, e !== null)) {
			t.child = null;
			do
				t = e.sibling, e.sibling = null, e = t;
			while (e !== null);
		}
	}
	function Pl(e) {
		var t = e.deletions;
		if (e.flags & 16) {
			if (t !== null) for (var n = 0; n < t.length; n++) {
				var r = t[n];
				al = r, Ll(r, e);
			}
			Nl(e);
		}
		if (e.subtreeFlags & 10256) for (e = e.child; e !== null;) Fl(e), e = e.sibling;
	}
	function Fl(e) {
		switch (e.tag) {
			case 0:
			case 11:
			case 15:
				Pl(e), e.flags & 2048 && Uc(9, e, e.return);
				break;
			case 3:
				Pl(e);
				break;
			case 12:
				Pl(e);
				break;
			case 22:
				var t = e.stateNode;
				e.memoizedState !== null && t._visibility & 2 && (e.return === null || e.return.tag !== 13) ? (t._visibility &= -3, Il(e)) : Pl(e);
				break;
			default: Pl(e);
		}
	}
	function Il(e) {
		var t = e.deletions;
		if (e.flags & 16) {
			if (t !== null) for (var n = 0; n < t.length; n++) {
				var r = t[n];
				al = r, Ll(r, e);
			}
			Nl(e);
		}
		for (e = e.child; e !== null;) {
			switch (t = e, t.tag) {
				case 0:
				case 11:
				case 15:
					Uc(8, t, t.return), Il(t);
					break;
				case 22:
					n = t.stateNode, n._visibility & 2 && (n._visibility &= -3, Il(t));
					break;
				default: Il(t);
			}
			e = e.sibling;
		}
	}
	function Ll(e, t) {
		for (; al !== null;) {
			var n = al;
			switch (n.tag) {
				case 0:
				case 11:
				case 15:
					Uc(8, n, t);
					break;
				case 23:
				case 22:
					if (n.memoizedState !== null && n.memoizedState.cachePool !== null) {
						var r = n.memoizedState.cachePool.pool;
						r != null && r.refCount++;
					}
					break;
				case 24: la(n.memoizedState.cache);
			}
			if (r = n.child, r !== null) r.return = n, al = r;
			else a: for (n = e; al !== null;) {
				r = al;
				var i = r.sibling, a = r.return;
				if (cl(r), r === n) {
					al = null;
					break a;
				}
				if (i !== null) {
					i.return = a, al = i;
					break a;
				}
				al = a;
			}
		}
	}
	var Rl = {
		getCacheForType: function(e) {
			var t = ta(sa), n = t.data.get(e);
			return n === void 0 && (n = e(), t.data.set(e, n)), n;
		},
		cacheSignal: function() {
			return ta(sa).controller.signal;
		}
	}, zl = typeof WeakMap == "function" ? WeakMap : Map, G = 0, K = null, q = null, J = 0, Y = 0, Bl = null, Vl = !1, Hl = !1, Ul = !1, Wl = 0, X = 0, Gl = 0, Kl = 0, ql = 0, Jl = 0, Yl = 0, Xl = null, Zl = null, Ql = !1, $l = 0, eu = 0, tu = Infinity, nu = null, ru = null, iu = 0, au = null, ou = null, su = 0, cu = 0, lu = null, uu = null, du = 0, fu = null;
	function pu() {
		return G & 2 && J !== 0 ? J & -J : O.T === null ? lt() : dd();
	}
	function mu() {
		if (Jl === 0) if (!(J & 536870912) || z) {
			var e = Je;
			Je <<= 1, !(Je & 3932160) && (Je = 262144), Jl = e;
		} else Jl = 536870912;
		return e = ro.current, e !== null && (e.flags |= 32), Jl;
	}
	function hu(e, t, n) {
		(e === K && (Y === 2 || Y === 9) || e.cancelPendingCommit !== null) && (Su(e, 0), yu(e, J, Jl, !1)), nt(e, n), (!(G & 2) || e !== K) && (e === K && (!(G & 2) && (Kl |= n), X === 4 && yu(e, J, Jl, !1)), rd(e));
	}
	function gu(e, t, n) {
		if (G & 6) throw Error(a(327));
		var r = !n && (t & 127) == 0 && (t & e.expiredLanes) === 0 || Qe(e, t), i = r ? Au(e, t) : Ou(e, t, !0), o = r;
		do {
			if (i === 0) {
				Hl && !r && yu(e, t, 0, !1);
				break;
			} else {
				if (n = e.current.alternate, o && !vu(n)) {
					i = Ou(e, t, !1), o = !1;
					continue;
				}
				if (i === 2) {
					if (o = t, e.errorRecoveryDisabledLanes & o) var s = 0;
					else s = e.pendingLanes & -536870913, s = s === 0 ? s & 536870912 ? 536870912 : 0 : s;
					if (s !== 0) {
						t = s;
						a: {
							var c = e;
							i = Xl;
							var l = c.current.memoizedState.isDehydrated;
							if (l && (Su(c, s).flags |= 256), s = Ou(c, s, !1), s !== 2) {
								if (Ul && !l) {
									c.errorRecoveryDisabledLanes |= o, Kl |= o, i = 4;
									break a;
								}
								o = Zl, Zl = i, o !== null && (Zl === null ? Zl = o : Zl.push.apply(Zl, o));
							}
							i = s;
						}
						if (o = !1, i !== 2) continue;
					}
				}
				if (i === 1) {
					Su(e, 0), yu(e, t, 0, !0);
					break;
				}
				a: {
					switch (r = e, o = i, o) {
						case 0:
						case 1: throw Error(a(345));
						case 4: if ((t & 4194048) !== t) break;
						case 6:
							yu(r, t, Jl, !Vl);
							break a;
						case 2:
							Zl = null;
							break;
						case 3:
						case 5: break;
						default: throw Error(a(329));
					}
					if ((t & 62914560) === t && (i = $l + 300 - je(), 10 < i)) {
						if (yu(r, t, Jl, !Vl), Ze(r, 0, !0) !== 0) break a;
						su = t, r.timeoutHandle = Kd(_u.bind(null, r, n, Zl, nu, Ql, t, Jl, Kl, Yl, Vl, o, "Throttled", -0, 0), i);
						break a;
					}
					_u(r, n, Zl, nu, Ql, t, Jl, Kl, Yl, Vl, o, null, -0, 0);
				}
			}
			break;
		} while (1);
		rd(e);
	}
	function _u(e, t, n, r, i, a, o, s, c, l, u, d, f, p) {
		if (e.timeoutHandle = -1, d = t.subtreeFlags, d & 8192 || (d & 16785408) == 16785408) {
			d = {
				stylesheets: null,
				count: 0,
				imgCount: 0,
				imgBytes: 0,
				suspenseyImages: [],
				waitingForImages: !0,
				waitingForViewTransition: !1,
				unsuspend: F
			}, Ml(t, a, d);
			var m = (a & 62914560) === a ? $l - je() : (a & 4194048) === a ? eu - je() : 0;
			if (m = qf(d, m), m !== null) {
				su = a, e.cancelPendingCommit = m(Lu.bind(null, e, t, a, n, r, i, o, s, c, u, d, null, f, p)), yu(e, a, o, !l);
				return;
			}
		}
		Lu(e, t, a, n, r, i, o, s, c);
	}
	function vu(e) {
		for (var t = e;;) {
			var n = t.tag;
			if ((n === 0 || n === 11 || n === 15) && t.flags & 16384 && (n = t.updateQueue, n !== null && (n = n.stores, n !== null))) for (var r = 0; r < n.length; r++) {
				var i = n[r], a = i.getSnapshot;
				i = i.value;
				try {
					if (!Cr(a(), i)) return !1;
				} catch {
					return !1;
				}
			}
			if (n = t.child, t.subtreeFlags & 16384 && n !== null) n.return = t, t = n;
			else {
				if (t === e) break;
				for (; t.sibling === null;) {
					if (t.return === null || t.return === e) return !0;
					t = t.return;
				}
				t.sibling.return = t.return, t = t.sibling;
			}
		}
		return !0;
	}
	function yu(e, t, n, r) {
		t &= ~ql, t &= ~Kl, e.suspendedLanes |= t, e.pingedLanes &= ~t, r && (e.warmLanes |= t), r = e.expirationTimes;
		for (var i = t; 0 < i;) {
			var a = 31 - Ue(i), o = 1 << a;
			r[a] = -1, i &= ~o;
		}
		n !== 0 && it(e, n, t);
	}
	function bu() {
		return G & 6 ? !0 : (id(0, !1), !1);
	}
	function xu() {
		if (q !== null) {
			if (Y === 0) var e = q.return;
			else e = q, qi = Ki = null, ko(e), Ma = null, Na = 0, e = q;
			for (; e !== null;) Vc(e.alternate, e), e = e.return;
			q = null;
		}
	}
	function Su(e, t) {
		var n = e.timeoutHandle;
		n !== -1 && (e.timeoutHandle = -1, qd(n)), n = e.cancelPendingCommit, n !== null && (e.cancelPendingCommit = null, n()), su = 0, xu(), K = e, q = n = di(e.current, null), J = t, Y = 0, Bl = null, Vl = !1, Hl = Qe(e, t), Ul = !1, Yl = Jl = ql = Kl = Gl = X = 0, Zl = Xl = null, Ql = !1, t & 8 && (t |= t & 32);
		var r = e.entangledLanes;
		if (r !== 0) for (e = e.entanglements, r &= t; 0 < r;) {
			var i = 31 - Ue(r), a = 1 << i;
			t |= e[i], r &= ~a;
		}
		return Wl = t, ti(), n;
	}
	function Cu(e, t) {
		B = null, O.H = zs, t === Sa || t === wa ? (t = Aa(), Y = 3) : t === Ca ? (t = Aa(), Y = 4) : Y = t === rc ? 8 : typeof t == "object" && t && typeof t.then == "function" ? 6 : 1, Bl = t, q === null && (X = 1, Zs(e, yi(t, e.current)));
	}
	function wu() {
		var e = ro.current;
		return e === null ? !0 : (J & 4194048) === J ? io === null : (J & 62914560) === J || J & 536870912 ? e === io : !1;
	}
	function Tu() {
		var e = O.H;
		return O.H = zs, e === null ? zs : e;
	}
	function Eu() {
		var e = O.A;
		return O.A = Rl, e;
	}
	function Du() {
		X = 4, Vl || (J & 4194048) !== J && ro.current !== null || (Hl = !0), !(Gl & 134217727) && !(Kl & 134217727) || K === null || yu(K, J, Jl, !1);
	}
	function Ou(e, t, n) {
		var r = G;
		G |= 2;
		var i = Tu(), a = Eu();
		(K !== e || J !== t) && (nu = null, Su(e, t)), t = !1;
		var o = X;
		a: do
			try {
				if (Y !== 0 && q !== null) {
					var s = q, c = Bl;
					switch (Y) {
						case 8:
							xu(), o = 6;
							break a;
						case 3:
						case 2:
						case 9:
						case 6:
							ro.current === null && (t = !0);
							var l = Y;
							if (Y = 0, Bl = null, Pu(e, s, c, l), n && Hl) {
								o = 0;
								break a;
							}
							break;
						default: l = Y, Y = 0, Bl = null, Pu(e, s, c, l);
					}
				}
				ku(), o = X;
				break;
			} catch (t) {
				Cu(e, t);
			}
		while (1);
		return t && e.shellSuspendCounter++, qi = Ki = null, G = r, O.H = i, O.A = a, q === null && (K = null, J = 0, ti()), o;
	}
	function ku() {
		for (; q !== null;) Mu(q);
	}
	function Au(e, t) {
		var n = G;
		G |= 2;
		var r = Tu(), i = Eu();
		K !== e || J !== t ? (nu = null, tu = je() + 500, Su(e, t)) : Hl = Qe(e, t);
		a: do
			try {
				if (Y !== 0 && q !== null) {
					t = q;
					var o = Bl;
					b: switch (Y) {
						case 1:
							Y = 0, Bl = null, Pu(e, t, o, 1);
							break;
						case 2:
						case 9:
							if (Ea(o)) {
								Y = 0, Bl = null, Nu(t);
								break;
							}
							t = function() {
								Y !== 2 && Y !== 9 || K !== e || (Y = 7), rd(e);
							}, o.then(t, t);
							break a;
						case 3:
							Y = 7;
							break a;
						case 4:
							Y = 5;
							break a;
						case 7:
							Ea(o) ? (Y = 0, Bl = null, Nu(t)) : (Y = 0, Bl = null, Pu(e, t, o, 7));
							break;
						case 5:
							var s = null;
							switch (q.tag) {
								case 26: s = q.memoizedState;
								case 5:
								case 27:
									var c = q;
									if (s ? Wf(s) : c.stateNode.complete) {
										Y = 0, Bl = null;
										var l = c.sibling;
										if (l !== null) q = l;
										else {
											var u = c.return;
											u === null ? q = null : (q = u, Fu(u));
										}
										break b;
									}
							}
							Y = 0, Bl = null, Pu(e, t, o, 5);
							break;
						case 6:
							Y = 0, Bl = null, Pu(e, t, o, 6);
							break;
						case 8:
							xu(), X = 6;
							break a;
						default: throw Error(a(462));
					}
				}
				ju();
				break;
			} catch (t) {
				Cu(e, t);
			}
		while (1);
		return qi = Ki = null, O.H = r, O.A = i, G = n, q === null ? (K = null, J = 0, ti(), X) : 0;
	}
	function ju() {
		for (; q !== null && !ke();) Mu(q);
	}
	function Mu(e) {
		var t = Nc(e.alternate, e, Wl);
		e.memoizedProps = e.pendingProps, t === null ? Fu(e) : q = t;
	}
	function Nu(e) {
		var t = e, n = t.alternate;
		switch (t.tag) {
			case 15:
			case 0:
				t = _c(n, t, t.pendingProps, t.type, void 0, J);
				break;
			case 11:
				t = _c(n, t, t.pendingProps, t.type.render, t.ref, J);
				break;
			case 5: ko(t);
			default: Vc(n, t), t = q = fi(t, Wl), t = Nc(n, t, Wl);
		}
		e.memoizedProps = e.pendingProps, t === null ? Fu(e) : q = t;
	}
	function Pu(e, t, n, r) {
		qi = Ki = null, ko(t), Ma = null, Na = 0;
		var i = t.return;
		try {
			if (nc(e, i, t, n, J)) {
				X = 1, Zs(e, yi(n, e.current)), q = null;
				return;
			}
		} catch (t) {
			if (i !== null) throw q = i, t;
			X = 1, Zs(e, yi(n, e.current)), q = null;
			return;
		}
		t.flags & 32768 ? (z || r === 1 ? e = !0 : Hl || J & 536870912 ? e = !1 : (Vl = e = !0, (r === 2 || r === 9 || r === 3 || r === 6) && (r = ro.current, r !== null && r.tag === 13 && (r.flags |= 16384))), Iu(t, e)) : Fu(t);
	}
	function Fu(e) {
		var t = e;
		do {
			if (t.flags & 32768) {
				Iu(t, Vl);
				return;
			}
			e = t.return;
			var n = zc(t.alternate, t, Wl);
			if (n !== null) {
				q = n;
				return;
			}
			if (t = t.sibling, t !== null) {
				q = t;
				return;
			}
			q = t = e;
		} while (t !== null);
		X === 0 && (X = 5);
	}
	function Iu(e, t) {
		do {
			var n = Bc(e.alternate, e);
			if (n !== null) {
				n.flags &= 32767, q = n;
				return;
			}
			if (n = e.return, n !== null && (n.flags |= 32768, n.subtreeFlags = 0, n.deletions = null), !t && (e = e.sibling, e !== null)) {
				q = e;
				return;
			}
			q = e = n;
		} while (e !== null);
		X = 6, q = null;
	}
	function Lu(e, t, n, r, i, o, s, c, l) {
		e.cancelPendingCommit = null;
		do
			Hu();
		while (iu !== 0);
		if (G & 6) throw Error(a(327));
		if (t !== null) {
			if (t === e.current) throw Error(a(177));
			if (o = t.lanes | t.childLanes, o |= ei, rt(e, n, o, s, c, l), e === K && (q = K = null, J = 0), ou = t, au = e, su = n, cu = o, lu = i, uu = r, t.subtreeFlags & 10256 || t.flags & 10256 ? (e.callbackNode = null, e.callbackPriority = 0, Xu(Fe, function() {
				return Uu(), null;
			})) : (e.callbackNode = null, e.callbackPriority = 0), r = (t.flags & 13878) != 0, t.subtreeFlags & 13878 || r) {
				r = O.T, O.T = null, i = k.p, k.p = 2, s = G, G |= 4;
				try {
					ol(e, t, n);
				} finally {
					G = s, k.p = i, O.T = r;
				}
			}
			iu = 1, Ru(), zu(), Bu();
		}
	}
	function Ru() {
		if (iu === 1) {
			iu = 0;
			var e = au, t = ou, n = (t.flags & 13878) != 0;
			if (t.subtreeFlags & 13878 || n) {
				n = O.T, O.T = null;
				var r = k.p;
				k.p = 2;
				var i = G;
				G |= 4;
				try {
					vl(t, e);
					var a = zd, o = Or(e.containerInfo), s = a.focusedElem, c = a.selectionRange;
					if (o !== s && s && s.ownerDocument && Dr(s.ownerDocument.documentElement, s)) {
						if (c !== null && kr(s)) {
							var l = c.start, u = c.end;
							if (u === void 0 && (u = l), "selectionStart" in s) s.selectionStart = l, s.selectionEnd = Math.min(u, s.value.length);
							else {
								var d = s.ownerDocument || document, f = d && d.defaultView || window;
								if (f.getSelection) {
									var p = f.getSelection(), m = s.textContent.length, h = Math.min(c.start, m), g = c.end === void 0 ? h : Math.min(c.end, m);
									!p.extend && h > g && (o = g, g = h, h = o);
									var _ = Er(s, h), v = Er(s, g);
									if (_ && v && (p.rangeCount !== 1 || p.anchorNode !== _.node || p.anchorOffset !== _.offset || p.focusNode !== v.node || p.focusOffset !== v.offset)) {
										var y = d.createRange();
										y.setStart(_.node, _.offset), p.removeAllRanges(), h > g ? (p.addRange(y), p.extend(v.node, v.offset)) : (y.setEnd(v.node, v.offset), p.addRange(y));
									}
								}
							}
						}
						for (d = [], p = s; p = p.parentNode;) p.nodeType === 1 && d.push({
							element: p,
							left: p.scrollLeft,
							top: p.scrollTop
						});
						for (typeof s.focus == "function" && s.focus(), s = 0; s < d.length; s++) {
							var b = d[s];
							b.element.scrollLeft = b.left, b.element.scrollTop = b.top;
						}
					}
					sp = !!Rd, zd = Rd = null;
				} finally {
					G = i, k.p = r, O.T = n;
				}
			}
			e.current = t, iu = 2;
		}
	}
	function zu() {
		if (iu === 2) {
			iu = 0;
			var e = au, t = ou, n = (t.flags & 8772) != 0;
			if (t.subtreeFlags & 8772 || n) {
				n = O.T, O.T = null;
				var r = k.p;
				k.p = 2;
				var i = G;
				G |= 4;
				try {
					sl(e, t.alternate, t);
				} finally {
					G = i, k.p = r, O.T = n;
				}
			}
			iu = 3;
		}
	}
	function Bu() {
		if (iu === 4 || iu === 3) {
			iu = 0, Ae();
			var e = au, t = ou, n = su, r = uu;
			t.subtreeFlags & 10256 || t.flags & 10256 ? iu = 5 : (iu = 0, ou = au = null, Vu(e, e.pendingLanes));
			var i = e.pendingLanes;
			if (i === 0 && (ru = null), ct(n), t = t.stateNode, Ve && typeof Ve.onCommitFiberRoot == "function") try {
				Ve.onCommitFiberRoot(Be, t, void 0, (t.current.flags & 128) == 128);
			} catch {}
			if (r !== null) {
				t = O.T, i = k.p, k.p = 2, O.T = null;
				try {
					for (var a = e.onRecoverableError, o = 0; o < r.length; o++) {
						var s = r[o];
						a(s.value, { componentStack: s.stack });
					}
				} finally {
					O.T = t, k.p = i;
				}
			}
			su & 3 && Hu(), rd(e), i = e.pendingLanes, n & 261930 && i & 42 ? e === fu ? du++ : (du = 0, fu = e) : du = 0, id(0, !1);
		}
	}
	function Vu(e, t) {
		(e.pooledCacheLanes &= t) === 0 && (t = e.pooledCache, t != null && (e.pooledCache = null, la(t)));
	}
	function Hu() {
		return Ru(), zu(), Bu(), Uu();
	}
	function Uu() {
		if (iu !== 5) return !1;
		var e = au, t = cu;
		cu = 0;
		var n = ct(su), r = O.T, i = k.p;
		try {
			k.p = 32 > n ? 32 : n, O.T = null, n = lu, lu = null;
			var o = au, s = su;
			if (iu = 0, ou = au = null, su = 0, G & 6) throw Error(a(331));
			var c = G;
			if (G |= 4, Fl(o.current), Dl(o, o.current, s, n), G = c, id(0, !1), Ve && typeof Ve.onPostCommitFiberRoot == "function") try {
				Ve.onPostCommitFiberRoot(Be, o);
			} catch {}
			return !0;
		} finally {
			k.p = i, O.T = r, Vu(e, t);
		}
	}
	function Wu(e, t, n) {
		t = yi(n, t), t = $s(e.stateNode, t, 2), e = Wa(e, t, 2), e !== null && (nt(e, 2), rd(e));
	}
	function Z(e, t, n) {
		if (e.tag === 3) Wu(e, e, n);
		else for (; t !== null;) {
			if (t.tag === 3) {
				Wu(t, e, n);
				break;
			} else if (t.tag === 1) {
				var r = t.stateNode;
				if (typeof t.type.getDerivedStateFromError == "function" || typeof r.componentDidCatch == "function" && (ru === null || !ru.has(r))) {
					e = yi(n, e), n = ec(2), r = Wa(t, n, 2), r !== null && (tc(n, r, t, e), nt(r, 2), rd(r));
					break;
				}
			}
			t = t.return;
		}
	}
	function Gu(e, t, n) {
		var r = e.pingCache;
		if (r === null) {
			r = e.pingCache = new zl();
			var i = /* @__PURE__ */ new Set();
			r.set(t, i);
		} else i = r.get(t), i === void 0 && (i = /* @__PURE__ */ new Set(), r.set(t, i));
		i.has(n) || (Ul = !0, i.add(n), e = Ku.bind(null, e, t, n), t.then(e, e));
	}
	function Ku(e, t, n) {
		var r = e.pingCache;
		r !== null && r.delete(t), e.pingedLanes |= e.suspendedLanes & n, e.warmLanes &= ~n, K === e && (J & n) === n && (X === 4 || X === 3 && (J & 62914560) === J && 300 > je() - $l ? !(G & 2) && Su(e, 0) : ql |= n, Yl === J && (Yl = 0)), rd(e);
	}
	function qu(e, t) {
		t === 0 && (t = et()), e = ii(e, t), e !== null && (nt(e, t), rd(e));
	}
	function Ju(e) {
		var t = e.memoizedState, n = 0;
		t !== null && (n = t.retryLane), qu(e, n);
	}
	function Yu(e, t) {
		var n = 0;
		switch (e.tag) {
			case 31:
			case 13:
				var r = e.stateNode, i = e.memoizedState;
				i !== null && (n = i.retryLane);
				break;
			case 19:
				r = e.stateNode;
				break;
			case 22:
				r = e.stateNode._retryCache;
				break;
			default: throw Error(a(314));
		}
		r !== null && r.delete(t), qu(e, n);
	}
	function Xu(e, t) {
		return M(e, t);
	}
	var Zu = null, Qu = null, $u = !1, ed = !1, td = !1, nd = 0;
	function rd(e) {
		e !== Qu && e.next === null && (Qu === null ? Zu = Qu = e : Qu = Qu.next = e), ed = !0, $u || ($u = !0, ud());
	}
	function id(e, t) {
		if (!td && ed) {
			td = !0;
			do
				for (var n = !1, r = Zu; r !== null;) {
					if (!t) if (e !== 0) {
						var i = r.pendingLanes;
						if (i === 0) var a = 0;
						else {
							var o = r.suspendedLanes, s = r.pingedLanes;
							a = (1 << 31 - Ue(42 | e) + 1) - 1, a &= i & ~(o & ~s), a = a & 201326741 ? a & 201326741 | 1 : a ? a | 2 : 0;
						}
						a !== 0 && (n = !0, ld(r, a));
					} else a = J, a = Ze(r, r === K ? a : 0, r.cancelPendingCommit !== null || r.timeoutHandle !== -1), !(a & 3) || Qe(r, a) || (n = !0, ld(r, a));
					r = r.next;
				}
			while (n);
			td = !1;
		}
	}
	function ad() {
		od();
	}
	function od() {
		ed = $u = !1;
		var e = 0;
		nd !== 0 && Gd() && (e = nd);
		for (var t = je(), n = null, r = Zu; r !== null;) {
			var i = r.next, a = sd(r, t);
			a === 0 ? (r.next = null, n === null ? Zu = i : n.next = i, i === null && (Qu = n)) : (n = r, (e !== 0 || a & 3) && (ed = !0)), r = i;
		}
		iu !== 0 && iu !== 5 || id(e, !1), nd !== 0 && (nd = 0);
	}
	function sd(e, t) {
		for (var n = e.suspendedLanes, r = e.pingedLanes, i = e.expirationTimes, a = e.pendingLanes & -62914561; 0 < a;) {
			var o = 31 - Ue(a), s = 1 << o, c = i[o];
			c === -1 ? ((s & n) === 0 || (s & r) !== 0) && (i[o] = $e(s, t)) : c <= t && (e.expiredLanes |= s), a &= ~s;
		}
		if (t = K, n = J, n = Ze(e, e === t ? n : 0, e.cancelPendingCommit !== null || e.timeoutHandle !== -1), r = e.callbackNode, n === 0 || e === t && (Y === 2 || Y === 9) || e.cancelPendingCommit !== null) return r !== null && r !== null && Oe(r), e.callbackNode = null, e.callbackPriority = 0;
		if (!(n & 3) || Qe(e, n)) {
			if (t = n & -n, t === e.callbackPriority) return t;
			switch (r !== null && Oe(r), ct(n)) {
				case 2:
				case 8:
					n = Pe;
					break;
				case 32:
					n = Fe;
					break;
				case 268435456:
					n = Le;
					break;
				default: n = Fe;
			}
			return r = cd.bind(null, e), n = M(n, r), e.callbackPriority = t, e.callbackNode = n, t;
		}
		return r !== null && r !== null && Oe(r), e.callbackPriority = 2, e.callbackNode = null, 2;
	}
	function cd(e, t) {
		if (iu !== 0 && iu !== 5) return e.callbackNode = null, e.callbackPriority = 0, null;
		var n = e.callbackNode;
		if (Hu() && e.callbackNode !== n) return null;
		var r = J;
		return r = Ze(e, e === K ? r : 0, e.cancelPendingCommit !== null || e.timeoutHandle !== -1), r === 0 ? null : (gu(e, r, t), sd(e, je()), e.callbackNode != null && e.callbackNode === n ? cd.bind(null, e) : null);
	}
	function ld(e, t) {
		if (Hu()) return null;
		gu(e, t, !0);
	}
	function ud() {
		Yd(function() {
			G & 6 ? M(Ne, ad) : od();
		});
	}
	function dd() {
		if (nd === 0) {
			var e = fa;
			e === 0 && (e = qe, qe <<= 1, !(qe & 261888) && (qe = 256)), nd = e;
		}
		return nd;
	}
	function fd(e) {
		return e == null || typeof e == "symbol" || typeof e == "boolean" ? null : typeof e == "function" ? e : nn("" + e);
	}
	function pd(e, t) {
		var n = t.ownerDocument.createElement("input");
		return n.name = t.name, n.value = t.value, e.id && n.setAttribute("form", e.id), t.parentNode.insertBefore(n, t), e = new FormData(e), n.parentNode.removeChild(n), e;
	}
	function md(e, t, n, r, i) {
		if (t === "submit" && n && n.stateNode === i) {
			var a = fd((i[pt] || null).action), o = r.submitter;
			o && (t = (t = o[pt] || null) ? fd(t.formAction) : o.getAttribute("formAction"), t !== null && (a = t, o = null));
			var s = new Sn("action", "action", null, r, i);
			e.push({
				event: s,
				listeners: [{
					instance: null,
					listener: function() {
						if (r.defaultPrevented) {
							if (nd !== 0) {
								var e = o ? pd(i, o) : new FormData(i);
								Ts(n, {
									pending: !0,
									data: e,
									method: i.method,
									action: a
								}, null, e);
							}
						} else typeof a == "function" && (s.preventDefault(), e = o ? pd(i, o) : new FormData(i), Ts(n, {
							pending: !0,
							data: e,
							method: i.method,
							action: a
						}, a, e));
					},
					currentTarget: i
				}]
			});
		}
	}
	for (var hd = 0; hd < Yr.length; hd++) {
		var gd = Yr[hd];
		Xr(gd.toLowerCase(), "on" + (gd[0].toUpperCase() + gd.slice(1)));
	}
	Xr(Vr, "onAnimationEnd"), Xr(Hr, "onAnimationIteration"), Xr(Ur, "onAnimationStart"), Xr("dblclick", "onDoubleClick"), Xr("focusin", "onFocus"), Xr("focusout", "onBlur"), Xr(Wr, "onTransitionRun"), Xr(Gr, "onTransitionStart"), Xr(Kr, "onTransitionCancel"), Xr(qr, "onTransitionEnd"), Dt("onMouseEnter", ["mouseout", "mouseover"]), Dt("onMouseLeave", ["mouseout", "mouseover"]), Dt("onPointerEnter", ["pointerout", "pointerover"]), Dt("onPointerLeave", ["pointerout", "pointerover"]), Et("onChange", "change click focusin focusout input keydown keyup selectionchange".split(" ")), Et("onSelect", "focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange".split(" ")), Et("onBeforeInput", [
		"compositionend",
		"keypress",
		"textInput",
		"paste"
	]), Et("onCompositionEnd", "compositionend focusout keydown keypress keyup mousedown".split(" ")), Et("onCompositionStart", "compositionstart focusout keydown keypress keyup mousedown".split(" ")), Et("onCompositionUpdate", "compositionupdate focusout keydown keypress keyup mousedown".split(" "));
	var _d = "abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting".split(" "), vd = new Set("beforetoggle cancel close invalid load scroll scrollend toggle".split(" ").concat(_d));
	function yd(e, t) {
		t = (t & 4) != 0;
		for (var n = 0; n < e.length; n++) {
			var r = e[n], i = r.event;
			r = r.listeners;
			a: {
				var a = void 0;
				if (t) for (var o = r.length - 1; 0 <= o; o--) {
					var s = r[o], c = s.instance, l = s.currentTarget;
					if (s = s.listener, c !== a && i.isPropagationStopped()) break a;
					a = s, i.currentTarget = l;
					try {
						a(i);
					} catch (e) {
						Zr(e);
					}
					i.currentTarget = null, a = c;
				}
				else for (o = 0; o < r.length; o++) {
					if (s = r[o], c = s.instance, l = s.currentTarget, s = s.listener, c !== a && i.isPropagationStopped()) break a;
					a = s, i.currentTarget = l;
					try {
						a(i);
					} catch (e) {
						Zr(e);
					}
					i.currentTarget = null, a = c;
				}
			}
		}
	}
	function Q(e, t) {
		var n = t[ht];
		n === void 0 && (n = t[ht] = /* @__PURE__ */ new Set());
		var r = e + "__bubble";
		n.has(r) || (Cd(t, e, 2, !1), n.add(r));
	}
	function bd(e, t, n) {
		var r = 0;
		t && (r |= 4), Cd(n, e, r, t);
	}
	var xd = "_reactListening" + Math.random().toString(36).slice(2);
	function Sd(e) {
		if (!e[xd]) {
			e[xd] = !0, wt.forEach(function(t) {
				t !== "selectionchange" && (vd.has(t) || bd(t, !1, e), bd(t, !0, e));
			});
			var t = e.nodeType === 9 ? e : e.ownerDocument;
			t === null || t[xd] || (t[xd] = !0, bd("selectionchange", !1, t));
		}
	}
	function Cd(e, t, n, r) {
		switch (mp(t)) {
			case 2:
				var i = cp;
				break;
			case 8:
				i = lp;
				break;
			default: i = up;
		}
		n = i.bind(null, t, n, e), i = void 0, !pn || t !== "touchstart" && t !== "touchmove" && t !== "wheel" || (i = !0), r ? i === void 0 ? e.addEventListener(t, n, !0) : e.addEventListener(t, n, {
			capture: !0,
			passive: i
		}) : i === void 0 ? e.addEventListener(t, n, !1) : e.addEventListener(t, n, { passive: i });
	}
	function wd(e, t, n, r, i) {
		var a = r;
		if (!(t & 1) && !(t & 2) && r !== null) a: for (;;) {
			if (r === null) return;
			var o = r.tag;
			if (o === 3 || o === 4) {
				var s = r.stateNode.containerInfo;
				if (s === i) break;
				if (o === 4) for (o = r.return; o !== null;) {
					var c = o.tag;
					if ((c === 3 || c === 4) && o.stateNode.containerInfo === i) return;
					o = o.return;
				}
				for (; s !== null;) {
					if (o = xt(s), o === null) return;
					if (c = o.tag, c === 5 || c === 6 || c === 26 || c === 27) {
						r = a = o;
						continue a;
					}
					s = s.parentNode;
				}
			}
			r = r.return;
		}
		un(function() {
			var r = a, i = an(n), o = [];
			a: {
				var s = Jr.get(e);
				if (s !== void 0) {
					var c = Sn, u = e;
					switch (e) {
						case "keypress": if (L(n) === 0) break a;
						case "keydown":
						case "keyup":
							c = Bn;
							break;
						case "focusin":
							u = "focus", c = jn;
							break;
						case "focusout":
							u = "blur", c = jn;
							break;
						case "beforeblur":
						case "afterblur":
							c = jn;
							break;
						case "click": if (n.button === 2) break a;
						case "auxclick":
						case "dblclick":
						case "mousedown":
						case "mousemove":
						case "mouseup":
						case "mouseout":
						case "mouseover":
						case "contextmenu":
							c = kn;
							break;
						case "drag":
						case "dragend":
						case "dragenter":
						case "dragexit":
						case "dragleave":
						case "dragover":
						case "dragstart":
						case "drop":
							c = An;
							break;
						case "touchcancel":
						case "touchend":
						case "touchmove":
						case "touchstart":
							c = Hn;
							break;
						case Vr:
						case Hr:
						case Ur:
							c = Mn;
							break;
						case qr:
							c = Un;
							break;
						case "scroll":
						case "scrollend":
							c = wn;
							break;
						case "wheel":
							c = Wn;
							break;
						case "copy":
						case "cut":
						case "paste":
							c = Nn;
							break;
						case "gotpointercapture":
						case "lostpointercapture":
						case "pointercancel":
						case "pointerdown":
						case "pointermove":
						case "pointerout":
						case "pointerover":
						case "pointerup":
							c = Vn;
							break;
						case "toggle":
						case "beforetoggle": c = Gn;
					}
					var d = (t & 4) != 0, f = !d && (e === "scroll" || e === "scrollend"), p = d ? s === null ? null : s + "Capture" : s;
					d = [];
					for (var m = r, h; m !== null;) {
						var g = m;
						if (h = g.stateNode, g = g.tag, g !== 5 && g !== 26 && g !== 27 || h === null || p === null || (g = dn(m, p), g != null && d.push(Td(m, g, h))), f) break;
						m = m.return;
					}
					0 < d.length && (s = new c(s, u, null, n, i), o.push({
						event: s,
						listeners: d
					}));
				}
			}
			if (!(t & 7)) {
				a: {
					if (s = e === "mouseover" || e === "pointerover", c = e === "mouseout" || e === "pointerout", s && n !== rn && (u = n.relatedTarget || n.fromElement) && (xt(u) || u[mt])) break a;
					if ((c || s) && (s = i.window === i ? i : (s = i.ownerDocument) ? s.defaultView || s.parentWindow : window, c ? (u = n.relatedTarget || n.toElement, c = r, u = u ? xt(u) : null, u !== null && (f = l(u), d = u.tag, u !== f || d !== 5 && d !== 27 && d !== 6) && (u = null)) : (c = null, u = r), c !== u)) {
						if (d = kn, g = "onMouseLeave", p = "onMouseEnter", m = "mouse", (e === "pointerout" || e === "pointerover") && (d = Vn, g = "onPointerLeave", p = "onPointerEnter", m = "pointer"), f = c == null ? s : St(c), h = u == null ? s : St(u), s = new d(g, m + "leave", c, n, i), s.target = f, s.relatedTarget = h, g = null, xt(i) === r && (d = new d(p, m + "enter", u, n, i), d.target = h, d.relatedTarget = f, g = d), f = g, c && u) b: {
							for (d = Dd, p = c, m = u, h = 0, g = p; g; g = d(g)) h++;
							g = 0;
							for (var _ = m; _; _ = d(_)) g++;
							for (; 0 < h - g;) p = d(p), h--;
							for (; 0 < g - h;) m = d(m), g--;
							for (; h--;) {
								if (p === m || m !== null && p === m.alternate) {
									d = p;
									break b;
								}
								p = d(p), m = d(m);
							}
							d = null;
						}
						else d = null;
						c !== null && Od(o, s, c, d, !1), u !== null && f !== null && Od(o, f, u, d, !0);
					}
				}
				a: {
					if (s = r ? St(r) : window, c = s.nodeName && s.nodeName.toLowerCase(), c === "select" || c === "input" && s.type === "file") var v = dr;
					else if (ar(s)) if (fr) v = xr;
					else {
						v = yr;
						var y = vr;
					}
					else c = s.nodeName, !c || c.toLowerCase() !== "input" || s.type !== "checkbox" && s.type !== "radio" ? r && $t(r.elementType) && (v = dr) : v = br;
					if (v &&= v(e, r)) {
						or(o, v, n, i);
						break a;
					}
					y && y(e, s, r), e === "focusout" && r && s.type === "number" && r.memoizedProps.value != null && Gt(s, "number", s.value);
				}
				switch (y = r ? St(r) : window, e) {
					case "focusin":
						(ar(y) || y.contentEditable === "true") && (jr = y, Mr = r, Nr = null);
						break;
					case "focusout":
						Nr = Mr = jr = null;
						break;
					case "mousedown":
						Pr = !0;
						break;
					case "contextmenu":
					case "mouseup":
					case "dragend":
						Pr = !1, Fr(o, n, i);
						break;
					case "selectionchange": if (Ar) break;
					case "keydown":
					case "keyup": Fr(o, n, i);
				}
				var b;
				if (qn) b: {
					switch (e) {
						case "compositionstart":
							var x = "onCompositionStart";
							break b;
						case "compositionend":
							x = "onCompositionEnd";
							break b;
						case "compositionupdate":
							x = "onCompositionUpdate";
							break b;
					}
					x = void 0;
				}
				else tr ? $n(e, n) && (x = "onCompositionEnd") : e === "keydown" && n.keyCode === 229 && (x = "onCompositionStart");
				x && (Xn && n.locale !== "ko" && (tr || x !== "onCompositionStart" ? x === "onCompositionEnd" && tr && (b = _n()) : (hn = i, gn = "value" in hn ? hn.value : hn.textContent, tr = !0)), y = Ed(r, x), 0 < y.length && (x = new Pn(x, e, null, n, i), o.push({
					event: x,
					listeners: y
				}), b ? x.data = b : (b = er(n), b !== null && (x.data = b)))), (b = Yn ? nr(e, n) : rr(e, n)) && (x = Ed(r, "onBeforeInput"), 0 < x.length && (y = new Pn("onBeforeInput", "beforeinput", null, n, i), o.push({
					event: y,
					listeners: x
				}), y.data = b)), md(o, e, r, n, i);
			}
			yd(o, t);
		});
	}
	function Td(e, t, n) {
		return {
			instance: e,
			listener: t,
			currentTarget: n
		};
	}
	function Ed(e, t) {
		for (var n = t + "Capture", r = []; e !== null;) {
			var i = e, a = i.stateNode;
			if (i = i.tag, i !== 5 && i !== 26 && i !== 27 || a === null || (i = dn(e, n), i != null && r.unshift(Td(e, i, a)), i = dn(e, t), i != null && r.push(Td(e, i, a))), e.tag === 3) return r;
			e = e.return;
		}
		return [];
	}
	function Dd(e) {
		if (e === null) return null;
		do
			e = e.return;
		while (e && e.tag !== 5 && e.tag !== 27);
		return e || null;
	}
	function Od(e, t, n, r, i) {
		for (var a = t._reactName, o = []; n !== null && n !== r;) {
			var s = n, c = s.alternate, l = s.stateNode;
			if (s = s.tag, c !== null && c === r) break;
			s !== 5 && s !== 26 && s !== 27 || l === null || (c = l, i ? (l = dn(n, a), l != null && o.unshift(Td(n, l, c))) : i || (l = dn(n, a), l != null && o.push(Td(n, l, c)))), n = n.return;
		}
		o.length !== 0 && e.push({
			event: t,
			listeners: o
		});
	}
	var kd = /\r\n?/g, Ad = /\u0000|\uFFFD/g;
	function jd(e) {
		return (typeof e == "string" ? e : "" + e).replace(kd, "\n").replace(Ad, "");
	}
	function Md(e, t) {
		return t = jd(t), jd(e) === t;
	}
	function $(e, t, n, r, i, o) {
		switch (n) {
			case "children":
				typeof r == "string" ? t === "body" || t === "textarea" && r === "" || Yt(e, r) : (typeof r == "number" || typeof r == "bigint") && t !== "body" && Yt(e, "" + r);
				break;
			case "className":
				Nt(e, "class", r);
				break;
			case "tabIndex":
				Nt(e, "tabindex", r);
				break;
			case "dir":
			case "role":
			case "viewBox":
			case "width":
			case "height":
				Nt(e, n, r);
				break;
			case "style":
				Qt(e, r, o);
				break;
			case "data": if (t !== "object") {
				Nt(e, "data", r);
				break;
			}
			case "src":
			case "href":
				if (r === "" && (t !== "a" || n !== "href")) {
					e.removeAttribute(n);
					break;
				}
				if (r == null || typeof r == "function" || typeof r == "symbol" || typeof r == "boolean") {
					e.removeAttribute(n);
					break;
				}
				r = nn("" + r), e.setAttribute(n, r);
				break;
			case "action":
			case "formAction":
				if (typeof r == "function") {
					e.setAttribute(n, "javascript:throw new Error('A React form was unexpectedly submitted. If you called form.submit() manually, consider using form.requestSubmit() instead. If you\\'re trying to use event.stopPropagation() in a submit event handler, consider also calling event.preventDefault().')");
					break;
				} else typeof o == "function" && (n === "formAction" ? (t !== "input" && $(e, t, "name", i.name, i, null), $(e, t, "formEncType", i.formEncType, i, null), $(e, t, "formMethod", i.formMethod, i, null), $(e, t, "formTarget", i.formTarget, i, null)) : ($(e, t, "encType", i.encType, i, null), $(e, t, "method", i.method, i, null), $(e, t, "target", i.target, i, null)));
				if (r == null || typeof r == "symbol" || typeof r == "boolean") {
					e.removeAttribute(n);
					break;
				}
				r = nn("" + r), e.setAttribute(n, r);
				break;
			case "onClick":
				r != null && (e.onclick = F);
				break;
			case "onScroll":
				r != null && Q("scroll", e);
				break;
			case "onScrollEnd":
				r != null && Q("scrollend", e);
				break;
			case "dangerouslySetInnerHTML":
				if (r != null) {
					if (typeof r != "object" || !("__html" in r)) throw Error(a(61));
					if (n = r.__html, n != null) {
						if (i.children != null) throw Error(a(60));
						e.innerHTML = n;
					}
				}
				break;
			case "multiple":
				e.multiple = r && typeof r != "function" && typeof r != "symbol";
				break;
			case "muted":
				e.muted = r && typeof r != "function" && typeof r != "symbol";
				break;
			case "suppressContentEditableWarning":
			case "suppressHydrationWarning":
			case "defaultValue":
			case "defaultChecked":
			case "innerHTML":
			case "ref": break;
			case "autoFocus": break;
			case "xlinkHref":
				if (r == null || typeof r == "function" || typeof r == "boolean" || typeof r == "symbol") {
					e.removeAttribute("xlink:href");
					break;
				}
				n = nn("" + r), e.setAttributeNS("http://www.w3.org/1999/xlink", "xlink:href", n);
				break;
			case "contentEditable":
			case "spellCheck":
			case "draggable":
			case "value":
			case "autoReverse":
			case "externalResourcesRequired":
			case "focusable":
			case "preserveAlpha":
				r != null && typeof r != "function" && typeof r != "symbol" ? e.setAttribute(n, "" + r) : e.removeAttribute(n);
				break;
			case "inert":
			case "allowFullScreen":
			case "async":
			case "autoPlay":
			case "controls":
			case "default":
			case "defer":
			case "disabled":
			case "disablePictureInPicture":
			case "disableRemotePlayback":
			case "formNoValidate":
			case "hidden":
			case "loop":
			case "noModule":
			case "noValidate":
			case "open":
			case "playsInline":
			case "readOnly":
			case "required":
			case "reversed":
			case "scoped":
			case "seamless":
			case "itemScope":
				r && typeof r != "function" && typeof r != "symbol" ? e.setAttribute(n, "") : e.removeAttribute(n);
				break;
			case "capture":
			case "download":
				!0 === r ? e.setAttribute(n, "") : !1 !== r && r != null && typeof r != "function" && typeof r != "symbol" ? e.setAttribute(n, r) : e.removeAttribute(n);
				break;
			case "cols":
			case "rows":
			case "size":
			case "span":
				r != null && typeof r != "function" && typeof r != "symbol" && !isNaN(r) && 1 <= r ? e.setAttribute(n, r) : e.removeAttribute(n);
				break;
			case "rowSpan":
			case "start":
				r == null || typeof r == "function" || typeof r == "symbol" || isNaN(r) ? e.removeAttribute(n) : e.setAttribute(n, r);
				break;
			case "popover":
				Q("beforetoggle", e), Q("toggle", e), Mt(e, "popover", r);
				break;
			case "xlinkActuate":
				Pt(e, "http://www.w3.org/1999/xlink", "xlink:actuate", r);
				break;
			case "xlinkArcrole":
				Pt(e, "http://www.w3.org/1999/xlink", "xlink:arcrole", r);
				break;
			case "xlinkRole":
				Pt(e, "http://www.w3.org/1999/xlink", "xlink:role", r);
				break;
			case "xlinkShow":
				Pt(e, "http://www.w3.org/1999/xlink", "xlink:show", r);
				break;
			case "xlinkTitle":
				Pt(e, "http://www.w3.org/1999/xlink", "xlink:title", r);
				break;
			case "xlinkType":
				Pt(e, "http://www.w3.org/1999/xlink", "xlink:type", r);
				break;
			case "xmlBase":
				Pt(e, "http://www.w3.org/XML/1998/namespace", "xml:base", r);
				break;
			case "xmlLang":
				Pt(e, "http://www.w3.org/XML/1998/namespace", "xml:lang", r);
				break;
			case "xmlSpace":
				Pt(e, "http://www.w3.org/XML/1998/namespace", "xml:space", r);
				break;
			case "is":
				Mt(e, "is", r);
				break;
			case "innerText":
			case "textContent": break;
			default: (!(2 < n.length) || n[0] !== "o" && n[0] !== "O" || n[1] !== "n" && n[1] !== "N") && (n = en.get(n) || n, Mt(e, n, r));
		}
	}
	function Nd(e, t, n, r, i, o) {
		switch (n) {
			case "style":
				Qt(e, r, o);
				break;
			case "dangerouslySetInnerHTML":
				if (r != null) {
					if (typeof r != "object" || !("__html" in r)) throw Error(a(61));
					if (n = r.__html, n != null) {
						if (i.children != null) throw Error(a(60));
						e.innerHTML = n;
					}
				}
				break;
			case "children":
				typeof r == "string" ? Yt(e, r) : (typeof r == "number" || typeof r == "bigint") && Yt(e, "" + r);
				break;
			case "onScroll":
				r != null && Q("scroll", e);
				break;
			case "onScrollEnd":
				r != null && Q("scrollend", e);
				break;
			case "onClick":
				r != null && (e.onclick = F);
				break;
			case "suppressContentEditableWarning":
			case "suppressHydrationWarning":
			case "innerHTML":
			case "ref": break;
			case "innerText":
			case "textContent": break;
			default: if (!Tt.hasOwnProperty(n)) a: {
				if (n[0] === "o" && n[1] === "n" && (i = n.endsWith("Capture"), t = n.slice(2, i ? n.length - 7 : void 0), o = e[pt] || null, o = o == null ? null : o[n], typeof o == "function" && e.removeEventListener(t, o, i), typeof r == "function")) {
					typeof o != "function" && o !== null && (n in e ? e[n] = null : e.hasAttribute(n) && e.removeAttribute(n)), e.addEventListener(t, r, i);
					break a;
				}
				n in e ? e[n] = r : !0 === r ? e.setAttribute(n, "") : Mt(e, n, r);
			}
		}
	}
	function Pd(e, t, n) {
		switch (t) {
			case "div":
			case "span":
			case "svg":
			case "path":
			case "a":
			case "g":
			case "p":
			case "li": break;
			case "img":
				Q("error", e), Q("load", e);
				var r = !1, i = !1, o;
				for (o in n) if (n.hasOwnProperty(o)) {
					var s = n[o];
					if (s != null) switch (o) {
						case "src":
							r = !0;
							break;
						case "srcSet":
							i = !0;
							break;
						case "children":
						case "dangerouslySetInnerHTML": throw Error(a(137, t));
						default: $(e, t, o, s, n, null);
					}
				}
				i && $(e, t, "srcSet", n.srcSet, n, null), r && $(e, t, "src", n.src, n, null);
				return;
			case "input":
				Q("invalid", e);
				var c = o = s = i = null, l = null, u = null;
				for (r in n) if (n.hasOwnProperty(r)) {
					var d = n[r];
					if (d != null) switch (r) {
						case "name":
							i = d;
							break;
						case "type":
							s = d;
							break;
						case "checked":
							l = d;
							break;
						case "defaultChecked":
							u = d;
							break;
						case "value":
							o = d;
							break;
						case "defaultValue":
							c = d;
							break;
						case "children":
						case "dangerouslySetInnerHTML":
							if (d != null) throw Error(a(137, t));
							break;
						default: $(e, t, r, d, n, null);
					}
				}
				Wt(e, o, c, l, u, s, i, !1);
				return;
			case "select":
				for (i in Q("invalid", e), r = s = o = null, n) if (n.hasOwnProperty(i) && (c = n[i], c != null)) switch (i) {
					case "value":
						o = c;
						break;
					case "defaultValue":
						s = c;
						break;
					case "multiple": r = c;
					default: $(e, t, i, c, n, null);
				}
				t = o, n = s, e.multiple = !!r, t == null ? n != null && Kt(e, !!r, n, !0) : Kt(e, !!r, t, !1);
				return;
			case "textarea":
				for (s in Q("invalid", e), o = i = r = null, n) if (n.hasOwnProperty(s) && (c = n[s], c != null)) switch (s) {
					case "value":
						r = c;
						break;
					case "defaultValue":
						i = c;
						break;
					case "children":
						o = c;
						break;
					case "dangerouslySetInnerHTML":
						if (c != null) throw Error(a(91));
						break;
					default: $(e, t, s, c, n, null);
				}
				Jt(e, r, i, o);
				return;
			case "option":
				for (l in n) if (n.hasOwnProperty(l) && (r = n[l], r != null)) switch (l) {
					case "selected":
						e.selected = r && typeof r != "function" && typeof r != "symbol";
						break;
					default: $(e, t, l, r, n, null);
				}
				return;
			case "dialog":
				Q("beforetoggle", e), Q("toggle", e), Q("cancel", e), Q("close", e);
				break;
			case "iframe":
			case "object":
				Q("load", e);
				break;
			case "video":
			case "audio":
				for (r = 0; r < _d.length; r++) Q(_d[r], e);
				break;
			case "image":
				Q("error", e), Q("load", e);
				break;
			case "details":
				Q("toggle", e);
				break;
			case "embed":
			case "source":
			case "link": Q("error", e), Q("load", e);
			case "area":
			case "base":
			case "br":
			case "col":
			case "hr":
			case "keygen":
			case "meta":
			case "param":
			case "track":
			case "wbr":
			case "menuitem":
				for (u in n) if (n.hasOwnProperty(u) && (r = n[u], r != null)) switch (u) {
					case "children":
					case "dangerouslySetInnerHTML": throw Error(a(137, t));
					default: $(e, t, u, r, n, null);
				}
				return;
			default: if ($t(t)) {
				for (d in n) n.hasOwnProperty(d) && (r = n[d], r !== void 0 && Nd(e, t, d, r, n, void 0));
				return;
			}
		}
		for (c in n) n.hasOwnProperty(c) && (r = n[c], r != null && $(e, t, c, r, n, null));
	}
	function Fd(e, t, n, r) {
		switch (t) {
			case "div":
			case "span":
			case "svg":
			case "path":
			case "a":
			case "g":
			case "p":
			case "li": break;
			case "input":
				var i = null, o = null, s = null, c = null, l = null, u = null, d = null;
				for (m in n) {
					var f = n[m];
					if (n.hasOwnProperty(m) && f != null) switch (m) {
						case "checked": break;
						case "value": break;
						case "defaultValue": l = f;
						default: r.hasOwnProperty(m) || $(e, t, m, null, r, f);
					}
				}
				for (var p in r) {
					var m = r[p];
					if (f = n[p], r.hasOwnProperty(p) && (m != null || f != null)) switch (p) {
						case "type":
							o = m;
							break;
						case "name":
							i = m;
							break;
						case "checked":
							u = m;
							break;
						case "defaultChecked":
							d = m;
							break;
						case "value":
							s = m;
							break;
						case "defaultValue":
							c = m;
							break;
						case "children":
						case "dangerouslySetInnerHTML":
							if (m != null) throw Error(a(137, t));
							break;
						default: m !== f && $(e, t, p, m, r, f);
					}
				}
				Ut(e, s, c, l, u, d, o, i);
				return;
			case "select":
				for (o in m = s = c = p = null, n) if (l = n[o], n.hasOwnProperty(o) && l != null) switch (o) {
					case "value": break;
					case "multiple": m = l;
					default: r.hasOwnProperty(o) || $(e, t, o, null, r, l);
				}
				for (i in r) if (o = r[i], l = n[i], r.hasOwnProperty(i) && (o != null || l != null)) switch (i) {
					case "value":
						p = o;
						break;
					case "defaultValue":
						c = o;
						break;
					case "multiple": s = o;
					default: o !== l && $(e, t, i, o, r, l);
				}
				t = c, n = s, r = m, p == null ? !!r != !!n && (t == null ? Kt(e, !!n, n ? [] : "", !1) : Kt(e, !!n, t, !0)) : Kt(e, !!n, p, !1);
				return;
			case "textarea":
				for (c in m = p = null, n) if (i = n[c], n.hasOwnProperty(c) && i != null && !r.hasOwnProperty(c)) switch (c) {
					case "value": break;
					case "children": break;
					default: $(e, t, c, null, r, i);
				}
				for (s in r) if (i = r[s], o = n[s], r.hasOwnProperty(s) && (i != null || o != null)) switch (s) {
					case "value":
						p = i;
						break;
					case "defaultValue":
						m = i;
						break;
					case "children": break;
					case "dangerouslySetInnerHTML":
						if (i != null) throw Error(a(91));
						break;
					default: i !== o && $(e, t, s, i, r, o);
				}
				qt(e, p, m);
				return;
			case "option":
				for (var h in n) if (p = n[h], n.hasOwnProperty(h) && p != null && !r.hasOwnProperty(h)) switch (h) {
					case "selected":
						e.selected = !1;
						break;
					default: $(e, t, h, null, r, p);
				}
				for (l in r) if (p = r[l], m = n[l], r.hasOwnProperty(l) && p !== m && (p != null || m != null)) switch (l) {
					case "selected":
						e.selected = p && typeof p != "function" && typeof p != "symbol";
						break;
					default: $(e, t, l, p, r, m);
				}
				return;
			case "img":
			case "link":
			case "area":
			case "base":
			case "br":
			case "col":
			case "embed":
			case "hr":
			case "keygen":
			case "meta":
			case "param":
			case "source":
			case "track":
			case "wbr":
			case "menuitem":
				for (var g in n) p = n[g], n.hasOwnProperty(g) && p != null && !r.hasOwnProperty(g) && $(e, t, g, null, r, p);
				for (u in r) if (p = r[u], m = n[u], r.hasOwnProperty(u) && p !== m && (p != null || m != null)) switch (u) {
					case "children":
					case "dangerouslySetInnerHTML":
						if (p != null) throw Error(a(137, t));
						break;
					default: $(e, t, u, p, r, m);
				}
				return;
			default: if ($t(t)) {
				for (var _ in n) p = n[_], n.hasOwnProperty(_) && p !== void 0 && !r.hasOwnProperty(_) && Nd(e, t, _, void 0, r, p);
				for (d in r) p = r[d], m = n[d], !r.hasOwnProperty(d) || p === m || p === void 0 && m === void 0 || Nd(e, t, d, p, r, m);
				return;
			}
		}
		for (var v in n) p = n[v], n.hasOwnProperty(v) && p != null && !r.hasOwnProperty(v) && $(e, t, v, null, r, p);
		for (f in r) p = r[f], m = n[f], !r.hasOwnProperty(f) || p === m || p == null && m == null || $(e, t, f, p, r, m);
	}
	function Id(e) {
		switch (e) {
			case "css":
			case "script":
			case "font":
			case "img":
			case "image":
			case "input":
			case "link": return !0;
			default: return !1;
		}
	}
	function Ld() {
		if (typeof performance.getEntriesByType == "function") {
			for (var e = 0, t = 0, n = performance.getEntriesByType("resource"), r = 0; r < n.length; r++) {
				var i = n[r], a = i.transferSize, o = i.initiatorType, s = i.duration;
				if (a && s && Id(o)) {
					for (o = 0, s = i.responseEnd, r += 1; r < n.length; r++) {
						var c = n[r], l = c.startTime;
						if (l > s) break;
						var u = c.transferSize, d = c.initiatorType;
						u && Id(d) && (c = c.responseEnd, o += u * (c < s ? 1 : (s - l) / (c - l)));
					}
					if (--r, t += 8 * (a + o) / (i.duration / 1e3), e++, 10 < e) break;
				}
			}
			if (0 < e) return t / e / 1e6;
		}
		return navigator.connection && (e = navigator.connection.downlink, typeof e == "number") ? e : 5;
	}
	var Rd = null, zd = null;
	function Bd(e) {
		return e.nodeType === 9 ? e : e.ownerDocument;
	}
	function Vd(e) {
		switch (e) {
			case "http://www.w3.org/2000/svg": return 1;
			case "http://www.w3.org/1998/Math/MathML": return 2;
			default: return 0;
		}
	}
	function Hd(e, t) {
		if (e === 0) switch (t) {
			case "svg": return 1;
			case "math": return 2;
			default: return 0;
		}
		return e === 1 && t === "foreignObject" ? 0 : e;
	}
	function Ud(e, t) {
		return e === "textarea" || e === "noscript" || typeof t.children == "string" || typeof t.children == "number" || typeof t.children == "bigint" || typeof t.dangerouslySetInnerHTML == "object" && t.dangerouslySetInnerHTML !== null && t.dangerouslySetInnerHTML.__html != null;
	}
	var Wd = null;
	function Gd() {
		var e = window.event;
		return e && e.type === "popstate" ? e === Wd ? !1 : (Wd = e, !0) : (Wd = null, !1);
	}
	var Kd = typeof setTimeout == "function" ? setTimeout : void 0, qd = typeof clearTimeout == "function" ? clearTimeout : void 0, Jd = typeof Promise == "function" ? Promise : void 0, Yd = typeof queueMicrotask == "function" ? queueMicrotask : Jd === void 0 ? Kd : function(e) {
		return Jd.resolve(null).then(e).catch(Xd);
	};
	function Xd(e) {
		setTimeout(function() {
			throw e;
		});
	}
	function Zd(e) {
		return e === "head";
	}
	function Qd(e, t) {
		var n = t, r = 0;
		do {
			var i = n.nextSibling;
			if (e.removeChild(n), i && i.nodeType === 8) if (n = i.data, n === "/$" || n === "/&") {
				if (r === 0) {
					e.removeChild(i), Np(t);
					return;
				}
				r--;
			} else if (n === "$" || n === "$?" || n === "$~" || n === "$!" || n === "&") r++;
			else if (n === "html") pf(e.ownerDocument.documentElement);
			else if (n === "head") {
				n = e.ownerDocument.head, pf(n);
				for (var a = n.firstChild; a;) {
					var o = a.nextSibling, s = a.nodeName;
					a[yt] || s === "SCRIPT" || s === "STYLE" || s === "LINK" && a.rel.toLowerCase() === "stylesheet" || n.removeChild(a), a = o;
				}
			} else n === "body" && pf(e.ownerDocument.body);
			n = i;
		} while (n);
		Np(t);
	}
	function $d(e, t) {
		var n = e;
		e = 0;
		do {
			var r = n.nextSibling;
			if (n.nodeType === 1 ? t ? (n._stashedDisplay = n.style.display, n.style.display = "none") : (n.style.display = n._stashedDisplay || "", n.getAttribute("style") === "" && n.removeAttribute("style")) : n.nodeType === 3 && (t ? (n._stashedText = n.nodeValue, n.nodeValue = "") : n.nodeValue = n._stashedText || ""), r && r.nodeType === 8) if (n = r.data, n === "/$") {
				if (e === 0) break;
				e--;
			} else n !== "$" && n !== "$?" && n !== "$~" && n !== "$!" || e++;
			n = r;
		} while (n);
	}
	function ef(e) {
		var t = e.firstChild;
		for (t && t.nodeType === 10 && (t = t.nextSibling); t;) {
			var n = t;
			switch (t = t.nextSibling, n.nodeName) {
				case "HTML":
				case "HEAD":
				case "BODY":
					ef(n), bt(n);
					continue;
				case "SCRIPT":
				case "STYLE": continue;
				case "LINK": if (n.rel.toLowerCase() === "stylesheet") continue;
			}
			e.removeChild(n);
		}
	}
	function tf(e, t, n, r) {
		for (; e.nodeType === 1;) {
			var i = n;
			if (e.nodeName.toLowerCase() !== t.toLowerCase()) {
				if (!r && (e.nodeName !== "INPUT" || e.type !== "hidden")) break;
			} else if (!r) if (t === "input" && e.type === "hidden") {
				var a = i.name == null ? null : "" + i.name;
				if (i.type === "hidden" && e.getAttribute("name") === a) return e;
			} else return e;
			else if (!e[yt]) switch (t) {
				case "meta":
					if (!e.hasAttribute("itemprop")) break;
					return e;
				case "link":
					if (a = e.getAttribute("rel"), a === "stylesheet" && e.hasAttribute("data-precedence") || a !== i.rel || e.getAttribute("href") !== (i.href == null || i.href === "" ? null : i.href) || e.getAttribute("crossorigin") !== (i.crossOrigin == null ? null : i.crossOrigin) || e.getAttribute("title") !== (i.title == null ? null : i.title)) break;
					return e;
				case "style":
					if (e.hasAttribute("data-precedence")) break;
					return e;
				case "script":
					if (a = e.getAttribute("src"), (a !== (i.src == null ? null : i.src) || e.getAttribute("type") !== (i.type == null ? null : i.type) || e.getAttribute("crossorigin") !== (i.crossOrigin == null ? null : i.crossOrigin)) && a && e.hasAttribute("async") && !e.hasAttribute("itemprop")) break;
					return e;
				default: return e;
			}
			if (e = cf(e.nextSibling), e === null) break;
		}
		return null;
	}
	function nf(e, t, n) {
		if (t === "") return null;
		for (; e.nodeType !== 3;) if ((e.nodeType !== 1 || e.nodeName !== "INPUT" || e.type !== "hidden") && !n || (e = cf(e.nextSibling), e === null)) return null;
		return e;
	}
	function rf(e, t) {
		for (; e.nodeType !== 8;) if ((e.nodeType !== 1 || e.nodeName !== "INPUT" || e.type !== "hidden") && !t || (e = cf(e.nextSibling), e === null)) return null;
		return e;
	}
	function af(e) {
		return e.data === "$?" || e.data === "$~";
	}
	function of(e) {
		return e.data === "$!" || e.data === "$?" && e.ownerDocument.readyState !== "loading";
	}
	function sf(e, t) {
		var n = e.ownerDocument;
		if (e.data === "$~") e._reactRetry = t;
		else if (e.data !== "$?" || n.readyState !== "loading") t();
		else {
			var r = function() {
				t(), n.removeEventListener("DOMContentLoaded", r);
			};
			n.addEventListener("DOMContentLoaded", r), e._reactRetry = r;
		}
	}
	function cf(e) {
		for (; e != null; e = e.nextSibling) {
			var t = e.nodeType;
			if (t === 1 || t === 3) break;
			if (t === 8) {
				if (t = e.data, t === "$" || t === "$!" || t === "$?" || t === "$~" || t === "&" || t === "F!" || t === "F") break;
				if (t === "/$" || t === "/&") return null;
			}
		}
		return e;
	}
	var lf = null;
	function uf(e) {
		e = e.nextSibling;
		for (var t = 0; e;) {
			if (e.nodeType === 8) {
				var n = e.data;
				if (n === "/$" || n === "/&") {
					if (t === 0) return cf(e.nextSibling);
					t--;
				} else n !== "$" && n !== "$!" && n !== "$?" && n !== "$~" && n !== "&" || t++;
			}
			e = e.nextSibling;
		}
		return null;
	}
	function df(e) {
		e = e.previousSibling;
		for (var t = 0; e;) {
			if (e.nodeType === 8) {
				var n = e.data;
				if (n === "$" || n === "$!" || n === "$?" || n === "$~" || n === "&") {
					if (t === 0) return e;
					t--;
				} else n !== "/$" && n !== "/&" || t++;
			}
			e = e.previousSibling;
		}
		return null;
	}
	function ff(e, t, n) {
		switch (t = Bd(n), e) {
			case "html":
				if (e = t.documentElement, !e) throw Error(a(452));
				return e;
			case "head":
				if (e = t.head, !e) throw Error(a(453));
				return e;
			case "body":
				if (e = t.body, !e) throw Error(a(454));
				return e;
			default: throw Error(a(451));
		}
	}
	function pf(e) {
		for (var t = e.attributes; t.length;) e.removeAttributeNode(t[0]);
		bt(e);
	}
	var mf = /* @__PURE__ */ new Map(), hf = /* @__PURE__ */ new Set();
	function gf(e) {
		return typeof e.getRootNode == "function" ? e.getRootNode() : e.nodeType === 9 ? e : e.ownerDocument;
	}
	var _f = k.d;
	k.d = {
		f: vf,
		r: yf,
		D: Sf,
		C: Cf,
		L: wf,
		m: Tf,
		X: Df,
		S: Ef,
		M: Of
	};
	function vf() {
		var e = _f.f(), t = bu();
		return e || t;
	}
	function yf(e) {
		var t = N(e);
		t !== null && t.tag === 5 && t.type === "form" ? Ds(t) : _f.r(e);
	}
	var bf = typeof document > "u" ? null : document;
	function xf(e, t, n) {
		var r = bf;
		if (r && typeof t == "string" && t) {
			var i = Ht(t);
			i = "link[rel=\"" + e + "\"][href=\"" + i + "\"]", typeof n == "string" && (i += "[crossorigin=\"" + n + "\"]"), hf.has(i) || (hf.add(i), e = {
				rel: e,
				crossOrigin: n,
				href: t
			}, r.querySelector(i) === null && (t = r.createElement("link"), Pd(t, "link", e), Ct(t), r.head.appendChild(t)));
		}
	}
	function Sf(e) {
		_f.D(e), xf("dns-prefetch", e, null);
	}
	function Cf(e, t) {
		_f.C(e, t), xf("preconnect", e, t);
	}
	function wf(e, t, n) {
		_f.L(e, t, n);
		var r = bf;
		if (r && e && t) {
			var i = "link[rel=\"preload\"][as=\"" + Ht(t) + "\"]";
			t === "image" && n && n.imageSrcSet ? (i += "[imagesrcset=\"" + Ht(n.imageSrcSet) + "\"]", typeof n.imageSizes == "string" && (i += "[imagesizes=\"" + Ht(n.imageSizes) + "\"]")) : i += "[href=\"" + Ht(e) + "\"]";
			var a = i;
			switch (t) {
				case "style":
					a = Af(e);
					break;
				case "script": a = Pf(e);
			}
			mf.has(a) || (e = h({
				rel: "preload",
				href: t === "image" && n && n.imageSrcSet ? void 0 : e,
				as: t
			}, n), mf.set(a, e), r.querySelector(i) !== null || t === "style" && r.querySelector(jf(a)) || t === "script" && r.querySelector(Ff(a)) || (t = r.createElement("link"), Pd(t, "link", e), Ct(t), r.head.appendChild(t)));
		}
	}
	function Tf(e, t) {
		_f.m(e, t);
		var n = bf;
		if (n && e) {
			var r = t && typeof t.as == "string" ? t.as : "script", i = "link[rel=\"modulepreload\"][as=\"" + Ht(r) + "\"][href=\"" + Ht(e) + "\"]", a = i;
			switch (r) {
				case "audioworklet":
				case "paintworklet":
				case "serviceworker":
				case "sharedworker":
				case "worker":
				case "script": a = Pf(e);
			}
			if (!mf.has(a) && (e = h({
				rel: "modulepreload",
				href: e
			}, t), mf.set(a, e), n.querySelector(i) === null)) {
				switch (r) {
					case "audioworklet":
					case "paintworklet":
					case "serviceworker":
					case "sharedworker":
					case "worker":
					case "script": if (n.querySelector(Ff(a))) return;
				}
				r = n.createElement("link"), Pd(r, "link", e), Ct(r), n.head.appendChild(r);
			}
		}
	}
	function Ef(e, t, n) {
		_f.S(e, t, n);
		var r = bf;
		if (r && e) {
			var i = P(r).hoistableStyles, a = Af(e);
			t ||= "default";
			var o = i.get(a);
			if (!o) {
				var s = {
					loading: 0,
					preload: null
				};
				if (o = r.querySelector(jf(a))) s.loading = 5;
				else {
					e = h({
						rel: "stylesheet",
						href: e,
						"data-precedence": t
					}, n), (n = mf.get(a)) && Rf(e, n);
					var c = o = r.createElement("link");
					Ct(c), Pd(c, "link", e), c._p = new Promise(function(e, t) {
						c.onload = e, c.onerror = t;
					}), c.addEventListener("load", function() {
						s.loading |= 1;
					}), c.addEventListener("error", function() {
						s.loading |= 2;
					}), s.loading |= 4, Lf(o, t, r);
				}
				o = {
					type: "stylesheet",
					instance: o,
					count: 1,
					state: s
				}, i.set(a, o);
			}
		}
	}
	function Df(e, t) {
		_f.X(e, t);
		var n = bf;
		if (n && e) {
			var r = P(n).hoistableScripts, i = Pf(e), a = r.get(i);
			a || (a = n.querySelector(Ff(i)), a || (e = h({
				src: e,
				async: !0
			}, t), (t = mf.get(i)) && zf(e, t), a = n.createElement("script"), Ct(a), Pd(a, "link", e), n.head.appendChild(a)), a = {
				type: "script",
				instance: a,
				count: 1,
				state: null
			}, r.set(i, a));
		}
	}
	function Of(e, t) {
		_f.M(e, t);
		var n = bf;
		if (n && e) {
			var r = P(n).hoistableScripts, i = Pf(e), a = r.get(i);
			a || (a = n.querySelector(Ff(i)), a || (e = h({
				src: e,
				async: !0,
				type: "module"
			}, t), (t = mf.get(i)) && zf(e, t), a = n.createElement("script"), Ct(a), Pd(a, "link", e), n.head.appendChild(a)), a = {
				type: "script",
				instance: a,
				count: 1,
				state: null
			}, r.set(i, a));
		}
	}
	function kf(e, t, n, r) {
		var i = (i = me.current) ? gf(i) : null;
		if (!i) throw Error(a(446));
		switch (e) {
			case "meta":
			case "title": return null;
			case "style": return typeof n.precedence == "string" && typeof n.href == "string" ? (t = Af(n.href), n = P(i).hoistableStyles, r = n.get(t), r || (r = {
				type: "style",
				instance: null,
				count: 0,
				state: null
			}, n.set(t, r)), r) : {
				type: "void",
				instance: null,
				count: 0,
				state: null
			};
			case "link":
				if (n.rel === "stylesheet" && typeof n.href == "string" && typeof n.precedence == "string") {
					e = Af(n.href);
					var o = P(i).hoistableStyles, s = o.get(e);
					if (s || (i = i.ownerDocument || i, s = {
						type: "stylesheet",
						instance: null,
						count: 0,
						state: {
							loading: 0,
							preload: null
						}
					}, o.set(e, s), (o = i.querySelector(jf(e))) && !o._p && (s.instance = o, s.state.loading = 5), mf.has(e) || (n = {
						rel: "preload",
						as: "style",
						href: n.href,
						crossOrigin: n.crossOrigin,
						integrity: n.integrity,
						media: n.media,
						hrefLang: n.hrefLang,
						referrerPolicy: n.referrerPolicy
					}, mf.set(e, n), o || Nf(i, e, n, s.state))), t && r === null) throw Error(a(528, ""));
					return s;
				}
				if (t && r !== null) throw Error(a(529, ""));
				return null;
			case "script": return t = n.async, n = n.src, typeof n == "string" && t && typeof t != "function" && typeof t != "symbol" ? (t = Pf(n), n = P(i).hoistableScripts, r = n.get(t), r || (r = {
				type: "script",
				instance: null,
				count: 0,
				state: null
			}, n.set(t, r)), r) : {
				type: "void",
				instance: null,
				count: 0,
				state: null
			};
			default: throw Error(a(444, e));
		}
	}
	function Af(e) {
		return "href=\"" + Ht(e) + "\"";
	}
	function jf(e) {
		return "link[rel=\"stylesheet\"][" + e + "]";
	}
	function Mf(e) {
		return h({}, e, {
			"data-precedence": e.precedence,
			precedence: null
		});
	}
	function Nf(e, t, n, r) {
		e.querySelector("link[rel=\"preload\"][as=\"style\"][" + t + "]") ? r.loading = 1 : (t = e.createElement("link"), r.preload = t, t.addEventListener("load", function() {
			return r.loading |= 1;
		}), t.addEventListener("error", function() {
			return r.loading |= 2;
		}), Pd(t, "link", n), Ct(t), e.head.appendChild(t));
	}
	function Pf(e) {
		return "[src=\"" + Ht(e) + "\"]";
	}
	function Ff(e) {
		return "script[async]" + e;
	}
	function If(e, t, n) {
		if (t.count++, t.instance === null) switch (t.type) {
			case "style":
				var r = e.querySelector("style[data-href~=\"" + Ht(n.href) + "\"]");
				if (r) return t.instance = r, Ct(r), r;
				var i = h({}, n, {
					"data-href": n.href,
					"data-precedence": n.precedence,
					href: null,
					precedence: null
				});
				return r = (e.ownerDocument || e).createElement("style"), Ct(r), Pd(r, "style", i), Lf(r, n.precedence, e), t.instance = r;
			case "stylesheet":
				i = Af(n.href);
				var o = e.querySelector(jf(i));
				if (o) return t.state.loading |= 4, t.instance = o, Ct(o), o;
				r = Mf(n), (i = mf.get(i)) && Rf(r, i), o = (e.ownerDocument || e).createElement("link"), Ct(o);
				var s = o;
				return s._p = new Promise(function(e, t) {
					s.onload = e, s.onerror = t;
				}), Pd(o, "link", r), t.state.loading |= 4, Lf(o, n.precedence, e), t.instance = o;
			case "script": return o = Pf(n.src), (i = e.querySelector(Ff(o))) ? (t.instance = i, Ct(i), i) : (r = n, (i = mf.get(o)) && (r = h({}, n), zf(r, i)), e = e.ownerDocument || e, i = e.createElement("script"), Ct(i), Pd(i, "link", r), e.head.appendChild(i), t.instance = i);
			case "void": return null;
			default: throw Error(a(443, t.type));
		}
		else t.type === "stylesheet" && !(t.state.loading & 4) && (r = t.instance, t.state.loading |= 4, Lf(r, n.precedence, e));
		return t.instance;
	}
	function Lf(e, t, n) {
		for (var r = n.querySelectorAll("link[rel=\"stylesheet\"][data-precedence],style[data-precedence]"), i = r.length ? r[r.length - 1] : null, a = i, o = 0; o < r.length; o++) {
			var s = r[o];
			if (s.dataset.precedence === t) a = s;
			else if (a !== i) break;
		}
		a ? a.parentNode.insertBefore(e, a.nextSibling) : (t = n.nodeType === 9 ? n.head : n, t.insertBefore(e, t.firstChild));
	}
	function Rf(e, t) {
		e.crossOrigin ??= t.crossOrigin, e.referrerPolicy ??= t.referrerPolicy, e.title ??= t.title;
	}
	function zf(e, t) {
		e.crossOrigin ??= t.crossOrigin, e.referrerPolicy ??= t.referrerPolicy, e.integrity ??= t.integrity;
	}
	var Bf = null;
	function Vf(e, t, n) {
		if (Bf === null) {
			var r = /* @__PURE__ */ new Map(), i = Bf = /* @__PURE__ */ new Map();
			i.set(n, r);
		} else i = Bf, r = i.get(n), r || (r = /* @__PURE__ */ new Map(), i.set(n, r));
		if (r.has(e)) return r;
		for (r.set(e, null), n = n.getElementsByTagName(e), i = 0; i < n.length; i++) {
			var a = n[i];
			if (!(a[yt] || a[ft] || e === "link" && a.getAttribute("rel") === "stylesheet") && a.namespaceURI !== "http://www.w3.org/2000/svg") {
				var o = a.getAttribute(t) || "";
				o = e + o;
				var s = r.get(o);
				s ? s.push(a) : r.set(o, [a]);
			}
		}
		return r;
	}
	function Hf(e, t, n) {
		e = e.ownerDocument || e, e.head.insertBefore(n, t === "title" ? e.querySelector("head > title") : null);
	}
	function Uf(e, t, n) {
		if (n === 1 || t.itemProp != null) return !1;
		switch (e) {
			case "meta":
			case "title": return !0;
			case "style":
				if (typeof t.precedence != "string" || typeof t.href != "string" || t.href === "") break;
				return !0;
			case "link":
				if (typeof t.rel != "string" || typeof t.href != "string" || t.href === "" || t.onLoad || t.onError) break;
				switch (t.rel) {
					case "stylesheet": return e = t.disabled, typeof t.precedence == "string" && e == null;
					default: return !0;
				}
			case "script": if (t.async && typeof t.async != "function" && typeof t.async != "symbol" && !t.onLoad && !t.onError && t.src && typeof t.src == "string") return !0;
		}
		return !1;
	}
	function Wf(e) {
		return !(e.type === "stylesheet" && !(e.state.loading & 3));
	}
	function Gf(e, t, n, r) {
		if (n.type === "stylesheet" && (typeof r.media != "string" || !1 !== matchMedia(r.media).matches) && !(n.state.loading & 4)) {
			if (n.instance === null) {
				var i = Af(r.href), a = t.querySelector(jf(i));
				if (a) {
					t = a._p, typeof t == "object" && t && typeof t.then == "function" && (e.count++, e = Jf.bind(e), t.then(e, e)), n.state.loading |= 4, n.instance = a, Ct(a);
					return;
				}
				a = t.ownerDocument || t, r = Mf(r), (i = mf.get(i)) && Rf(r, i), a = a.createElement("link"), Ct(a);
				var o = a;
				o._p = new Promise(function(e, t) {
					o.onload = e, o.onerror = t;
				}), Pd(a, "link", r), n.instance = a;
			}
			e.stylesheets === null && (e.stylesheets = /* @__PURE__ */ new Map()), e.stylesheets.set(n, t), (t = n.state.preload) && !(n.state.loading & 3) && (e.count++, n = Jf.bind(e), t.addEventListener("load", n), t.addEventListener("error", n));
		}
	}
	var Kf = 0;
	function qf(e, t) {
		return e.stylesheets && e.count === 0 && Xf(e, e.stylesheets), 0 < e.count || 0 < e.imgCount ? function(n) {
			var r = setTimeout(function() {
				if (e.stylesheets && Xf(e, e.stylesheets), e.unsuspend) {
					var t = e.unsuspend;
					e.unsuspend = null, t();
				}
			}, 6e4 + t);
			0 < e.imgBytes && Kf === 0 && (Kf = 62500 * Ld());
			var i = setTimeout(function() {
				if (e.waitingForImages = !1, e.count === 0 && (e.stylesheets && Xf(e, e.stylesheets), e.unsuspend)) {
					var t = e.unsuspend;
					e.unsuspend = null, t();
				}
			}, (e.imgBytes > Kf ? 50 : 800) + t);
			return e.unsuspend = n, function() {
				e.unsuspend = null, clearTimeout(r), clearTimeout(i);
			};
		} : null;
	}
	function Jf() {
		if (this.count--, this.count === 0 && (this.imgCount === 0 || !this.waitingForImages)) {
			if (this.stylesheets) Xf(this, this.stylesheets);
			else if (this.unsuspend) {
				var e = this.unsuspend;
				this.unsuspend = null, e();
			}
		}
	}
	var Yf = null;
	function Xf(e, t) {
		e.stylesheets = null, e.unsuspend !== null && (e.count++, Yf = /* @__PURE__ */ new Map(), t.forEach(Zf, e), Yf = null, Jf.call(e));
	}
	function Zf(e, t) {
		if (!(t.state.loading & 4)) {
			var n = Yf.get(e);
			if (n) var r = n.get(null);
			else {
				n = /* @__PURE__ */ new Map(), Yf.set(e, n);
				for (var i = e.querySelectorAll("link[data-precedence],style[data-precedence]"), a = 0; a < i.length; a++) {
					var o = i[a];
					(o.nodeName === "LINK" || o.getAttribute("media") !== "not all") && (n.set(o.dataset.precedence, o), r = o);
				}
				r && n.set(null, r);
			}
			i = t.instance, o = i.getAttribute("data-precedence"), a = n.get(o) || r, a === r && n.set(null, i), n.set(o, i), this.count++, r = Jf.bind(this), i.addEventListener("load", r), i.addEventListener("error", r), a ? a.parentNode.insertBefore(i, a.nextSibling) : (e = e.nodeType === 9 ? e.head : e, e.insertBefore(i, e.firstChild)), t.state.loading |= 4;
		}
	}
	var Qf = {
		$$typeof: C,
		Provider: null,
		Consumer: null,
		_currentValue: ce,
		_currentValue2: ce,
		_threadCount: 0
	};
	function $f(e, t, n, r, i, a, o, s, c) {
		this.tag = 1, this.containerInfo = e, this.pingCache = this.current = this.pendingChildren = null, this.timeoutHandle = -1, this.callbackNode = this.next = this.pendingContext = this.context = this.cancelPendingCommit = null, this.callbackPriority = 0, this.expirationTimes = tt(-1), this.entangledLanes = this.shellSuspendCounter = this.errorRecoveryDisabledLanes = this.expiredLanes = this.warmLanes = this.pingedLanes = this.suspendedLanes = this.pendingLanes = 0, this.entanglements = tt(0), this.hiddenUpdates = tt(null), this.identifierPrefix = r, this.onUncaughtError = i, this.onCaughtError = a, this.onRecoverableError = o, this.pooledCache = null, this.pooledCacheLanes = 0, this.formState = c, this.incompleteTransitions = /* @__PURE__ */ new Map();
	}
	function ep(e, t, n, r, i, a, o, s, c, l, u, d) {
		return e = new $f(e, t, n, o, c, l, u, d, s), t = 1, !0 === a && (t |= 24), a = li(3, null, null, t), e.current = a, a.stateNode = e, t = ca(), t.refCount++, e.pooledCache = t, t.refCount++, a.memoizedState = {
			element: r,
			isDehydrated: n,
			cache: t
		}, Va(a), e;
	}
	function tp(e) {
		return e ? (e = si, e) : si;
	}
	function np(e, t, n, r, i, a) {
		i = tp(i), r.context === null ? r.context = i : r.pendingContext = i, r = Ua(t), r.payload = { element: n }, a = a === void 0 ? null : a, a !== null && (r.callback = a), n = Wa(e, r, t), n !== null && (hu(n, e, t), Ga(n, e, t));
	}
	function rp(e, t) {
		if (e = e.memoizedState, e !== null && e.dehydrated !== null) {
			var n = e.retryLane;
			e.retryLane = n !== 0 && n < t ? n : t;
		}
	}
	function ip(e, t) {
		rp(e, t), (e = e.alternate) && rp(e, t);
	}
	function ap(e) {
		if (e.tag === 13 || e.tag === 31) {
			var t = ii(e, 67108864);
			t !== null && hu(t, e, 67108864), ip(e, 67108864);
		}
	}
	function op(e) {
		if (e.tag === 13 || e.tag === 31) {
			var t = pu();
			t = st(t);
			var n = ii(e, t);
			n !== null && hu(n, e, t), ip(e, t);
		}
	}
	var sp = !0;
	function cp(e, t, n, r) {
		var i = O.T;
		O.T = null;
		var a = k.p;
		try {
			k.p = 2, up(e, t, n, r);
		} finally {
			k.p = a, O.T = i;
		}
	}
	function lp(e, t, n, r) {
		var i = O.T;
		O.T = null;
		var a = k.p;
		try {
			k.p = 8, up(e, t, n, r);
		} finally {
			k.p = a, O.T = i;
		}
	}
	function up(e, t, n, r) {
		if (sp) {
			var i = dp(r);
			if (i === null) wd(e, t, r, fp, n), Cp(e, r);
			else if (Tp(i, e, t, n, r)) r.stopPropagation();
			else if (Cp(e, r), t & 4 && -1 < Sp.indexOf(e)) {
				for (; i !== null;) {
					var a = N(i);
					if (a !== null) switch (a.tag) {
						case 3:
							if (a = a.stateNode, a.current.memoizedState.isDehydrated) {
								var o = Xe(a.pendingLanes);
								if (o !== 0) {
									var s = a;
									for (s.pendingLanes |= 2, s.entangledLanes |= 2; o;) {
										var c = 1 << 31 - Ue(o);
										s.entanglements[1] |= c, o &= ~c;
									}
									rd(a), !(G & 6) && (tu = je() + 500, id(0, !1));
								}
							}
							break;
						case 31:
						case 13: s = ii(a, 2), s !== null && hu(s, a, 2), bu(), ip(a, 2);
					}
					if (a = dp(r), a === null && wd(e, t, r, fp, n), a === i) break;
					i = a;
				}
				i !== null && r.stopPropagation();
			} else wd(e, t, r, null, n);
		}
	}
	function dp(e) {
		return e = an(e), pp(e);
	}
	var fp = null;
	function pp(e) {
		if (fp = null, e = xt(e), e !== null) {
			var t = l(e);
			if (t === null) e = null;
			else {
				var n = t.tag;
				if (n === 13) {
					if (e = u(t), e !== null) return e;
					e = null;
				} else if (n === 31) {
					if (e = d(t), e !== null) return e;
					e = null;
				} else if (n === 3) {
					if (t.stateNode.current.memoizedState.isDehydrated) return t.tag === 3 ? t.stateNode.containerInfo : null;
					e = null;
				} else t !== e && (e = null);
			}
		}
		return fp = e, null;
	}
	function mp(e) {
		switch (e) {
			case "beforetoggle":
			case "cancel":
			case "click":
			case "close":
			case "contextmenu":
			case "copy":
			case "cut":
			case "auxclick":
			case "dblclick":
			case "dragend":
			case "dragstart":
			case "drop":
			case "focusin":
			case "focusout":
			case "input":
			case "invalid":
			case "keydown":
			case "keypress":
			case "keyup":
			case "mousedown":
			case "mouseup":
			case "paste":
			case "pause":
			case "play":
			case "pointercancel":
			case "pointerdown":
			case "pointerup":
			case "ratechange":
			case "reset":
			case "resize":
			case "seeked":
			case "submit":
			case "toggle":
			case "touchcancel":
			case "touchend":
			case "touchstart":
			case "volumechange":
			case "change":
			case "selectionchange":
			case "textInput":
			case "compositionstart":
			case "compositionend":
			case "compositionupdate":
			case "beforeblur":
			case "afterblur":
			case "beforeinput":
			case "blur":
			case "fullscreenchange":
			case "focus":
			case "hashchange":
			case "popstate":
			case "select":
			case "selectstart": return 2;
			case "drag":
			case "dragenter":
			case "dragexit":
			case "dragleave":
			case "dragover":
			case "mousemove":
			case "mouseout":
			case "mouseover":
			case "pointermove":
			case "pointerout":
			case "pointerover":
			case "scroll":
			case "touchmove":
			case "wheel":
			case "mouseenter":
			case "mouseleave":
			case "pointerenter":
			case "pointerleave": return 8;
			case "message": switch (Me()) {
				case Ne: return 2;
				case Pe: return 8;
				case Fe:
				case Ie: return 32;
				case Le: return 268435456;
				default: return 32;
			}
			default: return 32;
		}
	}
	var hp = !1, gp = null, _p = null, vp = null, yp = /* @__PURE__ */ new Map(), bp = /* @__PURE__ */ new Map(), xp = [], Sp = "mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset".split(" ");
	function Cp(e, t) {
		switch (e) {
			case "focusin":
			case "focusout":
				gp = null;
				break;
			case "dragenter":
			case "dragleave":
				_p = null;
				break;
			case "mouseover":
			case "mouseout":
				vp = null;
				break;
			case "pointerover":
			case "pointerout":
				yp.delete(t.pointerId);
				break;
			case "gotpointercapture":
			case "lostpointercapture": bp.delete(t.pointerId);
		}
	}
	function wp(e, t, n, r, i, a) {
		return e === null || e.nativeEvent !== a ? (e = {
			blockedOn: t,
			domEventName: n,
			eventSystemFlags: r,
			nativeEvent: a,
			targetContainers: [i]
		}, t !== null && (t = N(t), t !== null && ap(t)), e) : (e.eventSystemFlags |= r, t = e.targetContainers, i !== null && t.indexOf(i) === -1 && t.push(i), e);
	}
	function Tp(e, t, n, r, i) {
		switch (t) {
			case "focusin": return gp = wp(gp, e, t, n, r, i), !0;
			case "dragenter": return _p = wp(_p, e, t, n, r, i), !0;
			case "mouseover": return vp = wp(vp, e, t, n, r, i), !0;
			case "pointerover":
				var a = i.pointerId;
				return yp.set(a, wp(yp.get(a) || null, e, t, n, r, i)), !0;
			case "gotpointercapture": return a = i.pointerId, bp.set(a, wp(bp.get(a) || null, e, t, n, r, i)), !0;
		}
		return !1;
	}
	function Ep(e) {
		var t = xt(e.target);
		if (t !== null) {
			var n = l(t);
			if (n !== null) {
				if (t = n.tag, t === 13) {
					if (t = u(n), t !== null) {
						e.blockedOn = t, ut(e.priority, function() {
							op(n);
						});
						return;
					}
				} else if (t === 31) {
					if (t = d(n), t !== null) {
						e.blockedOn = t, ut(e.priority, function() {
							op(n);
						});
						return;
					}
				} else if (t === 3 && n.stateNode.current.memoizedState.isDehydrated) {
					e.blockedOn = n.tag === 3 ? n.stateNode.containerInfo : null;
					return;
				}
			}
		}
		e.blockedOn = null;
	}
	function Dp(e) {
		if (e.blockedOn !== null) return !1;
		for (var t = e.targetContainers; 0 < t.length;) {
			var n = dp(e.nativeEvent);
			if (n === null) {
				n = e.nativeEvent;
				var r = new n.constructor(n.type, n);
				rn = r, n.target.dispatchEvent(r), rn = null;
			} else return t = N(n), t !== null && ap(t), e.blockedOn = n, !1;
			t.shift();
		}
		return !0;
	}
	function Op(e, t, n) {
		Dp(e) && n.delete(t);
	}
	function kp() {
		hp = !1, gp !== null && Dp(gp) && (gp = null), _p !== null && Dp(_p) && (_p = null), vp !== null && Dp(vp) && (vp = null), yp.forEach(Op), bp.forEach(Op);
	}
	function Ap(e, n) {
		e.blockedOn === n && (e.blockedOn = null, hp || (hp = !0, t.unstable_scheduleCallback(t.unstable_NormalPriority, kp)));
	}
	var jp = null;
	function Mp(e) {
		jp !== e && (jp = e, t.unstable_scheduleCallback(t.unstable_NormalPriority, function() {
			jp === e && (jp = null);
			for (var t = 0; t < e.length; t += 3) {
				var n = e[t], r = e[t + 1], i = e[t + 2];
				if (typeof r != "function") {
					if (pp(r || n) === null) continue;
					break;
				}
				var a = N(n);
				a !== null && (e.splice(t, 3), t -= 3, Ts(a, {
					pending: !0,
					data: i,
					method: n.method,
					action: r
				}, r, i));
			}
		}));
	}
	function Np(e) {
		function t(t) {
			return Ap(t, e);
		}
		gp !== null && Ap(gp, e), _p !== null && Ap(_p, e), vp !== null && Ap(vp, e), yp.forEach(t), bp.forEach(t);
		for (var n = 0; n < xp.length; n++) {
			var r = xp[n];
			r.blockedOn === e && (r.blockedOn = null);
		}
		for (; 0 < xp.length && (n = xp[0], n.blockedOn === null);) Ep(n), n.blockedOn === null && xp.shift();
		if (n = (e.ownerDocument || e).$$reactFormReplay, n != null) for (r = 0; r < n.length; r += 3) {
			var i = n[r], a = n[r + 1], o = i[pt] || null;
			if (typeof a == "function") o || Mp(n);
			else if (o) {
				var s = null;
				if (a && a.hasAttribute("formAction")) {
					if (i = a, o = a[pt] || null) s = o.formAction;
					else if (pp(i) !== null) continue;
				} else s = o.action;
				typeof s == "function" ? n[r + 1] = s : (n.splice(r, 3), r -= 3), Mp(n);
			}
		}
	}
	function Pp() {
		function e(e) {
			e.canIntercept && e.info === "react-transition" && e.intercept({
				handler: function() {
					return new Promise(function(e) {
						return i = e;
					});
				},
				focusReset: "manual",
				scroll: "manual"
			});
		}
		function t() {
			i !== null && (i(), i = null), r || setTimeout(n, 20);
		}
		function n() {
			if (!r && !navigation.transition) {
				var e = navigation.currentEntry;
				e && e.url != null && navigation.navigate(e.url, {
					state: e.getState(),
					info: "react-transition",
					history: "replace"
				});
			}
		}
		if (typeof navigation == "object") {
			var r = !1, i = null;
			return navigation.addEventListener("navigate", e), navigation.addEventListener("navigatesuccess", t), navigation.addEventListener("navigateerror", t), setTimeout(n, 100), function() {
				r = !0, navigation.removeEventListener("navigate", e), navigation.removeEventListener("navigatesuccess", t), navigation.removeEventListener("navigateerror", t), i !== null && (i(), i = null);
			};
		}
	}
	function Fp(e) {
		this._internalRoot = e;
	}
	Ip.prototype.render = Fp.prototype.render = function(e) {
		var t = this._internalRoot;
		if (t === null) throw Error(a(409));
		var n = t.current;
		np(n, pu(), e, t, null, null);
	}, Ip.prototype.unmount = Fp.prototype.unmount = function() {
		var e = this._internalRoot;
		if (e !== null) {
			this._internalRoot = null;
			var t = e.containerInfo;
			np(e.current, 2, null, e, null, null), bu(), t[mt] = null;
		}
	};
	function Ip(e) {
		this._internalRoot = e;
	}
	Ip.prototype.unstable_scheduleHydration = function(e) {
		if (e) {
			var t = lt();
			e = {
				blockedOn: null,
				target: e,
				priority: t
			};
			for (var n = 0; n < xp.length && t !== 0 && t < xp[n].priority; n++);
			xp.splice(n, 0, e), n === 0 && Ep(e);
		}
	};
	var Lp = n.version;
	if (Lp !== "19.2.8") throw Error(a(527, Lp, "19.2.8"));
	k.findDOMNode = function(e) {
		var t = e._reactInternals;
		if (t === void 0) throw typeof e.render == "function" ? Error(a(188)) : (e = Object.keys(e).join(","), Error(a(268, e)));
		return e = p(t), e = e === null ? null : m(e), e = e === null ? null : e.stateNode, e;
	};
	var Rp = {
		bundleType: 0,
		version: "19.2.8",
		rendererPackageName: "react-dom",
		currentDispatcherRef: O,
		reconcilerVersion: "19.2.8"
	};
	if (typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ < "u") {
		var zp = __REACT_DEVTOOLS_GLOBAL_HOOK__;
		if (!zp.isDisabled && zp.supportsFiber) try {
			Be = zp.inject(Rp), Ve = zp;
		} catch {}
	}
	e.createRoot = function(e, t) {
		if (!s(e)) throw Error(a(299));
		var n = !1, r = "", i = Js, o = Ys, c = Xs;
		return t != null && (!0 === t.unstable_strictMode && (n = !0), t.identifierPrefix !== void 0 && (r = t.identifierPrefix), t.onUncaughtError !== void 0 && (i = t.onUncaughtError), t.onCaughtError !== void 0 && (o = t.onCaughtError), t.onRecoverableError !== void 0 && (c = t.onRecoverableError)), t = ep(e, 1, !1, null, null, n, r, null, i, o, c, Pp), e[mt] = t.current, Sd(e), new Fp(t);
	};
})), u = /* @__PURE__ */ t(((e, t) => {
	function n() {
		if (!(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ > "u" || typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE != "function")) try {
			__REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(n);
		} catch (e) {
			console.error(e);
		}
	}
	n(), t.exports = l();
})), d = i(), f = c(), p = u(), m = "jobhunter:page-rendered";
function h(e, t) {
	e.dispatchEvent(new CustomEvent(m, { detail: { page: t } }));
}
function g(e, t) {
	let n = (e) => {
		let n = e.detail?.page;
		n && t(n);
	};
	return e.addEventListener(m, n), () => e.removeEventListener(m, n);
}
//#endregion
//#region node_modules/lucide-react/dist/esm/shared/src/utils/mergeClasses.mjs
var _ = (...e) => e.filter((e, t, n) => !!e && e.trim() !== "" && n.indexOf(e) === t).join(" ").trim(), v = (e) => e.replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase(), y = (e) => e.replace(/^([A-Z])|[\s-_]+(\w)/g, (e, t, n) => n ? n.toUpperCase() : t.toLowerCase()), b = (e) => {
	let t = y(e);
	return t.charAt(0).toUpperCase() + t.slice(1);
}, x = {
	xmlns: "http://www.w3.org/2000/svg",
	width: 24,
	height: 24,
	viewBox: "0 0 24 24",
	fill: "none",
	stroke: "currentColor",
	strokeWidth: 2,
	strokeLinecap: "round",
	strokeLinejoin: "round"
}, S = (e) => {
	for (let t in e) if (t.startsWith("aria-") || t === "role" || t === "title") return !0;
	return !1;
}, C = (0, d.createContext)({}), w = () => (0, d.useContext)(C), T = (0, d.forwardRef)(({ color: e, size: t, strokeWidth: n, absoluteStrokeWidth: r, className: i = "", children: a, iconNode: o, ...s }, c) => {
	let { size: l = 24, strokeWidth: u = 2, absoluteStrokeWidth: f = !1, color: p = "currentColor", className: m = "" } = w() ?? {}, h = r ?? f ? Number(n ?? u) * 24 / Number(t ?? l) : n ?? u;
	return (0, d.createElement)("svg", {
		ref: c,
		...x,
		width: t ?? l ?? x.width,
		height: t ?? l ?? x.height,
		stroke: e ?? p,
		strokeWidth: h,
		className: _("lucide", m, i),
		...!a && !S(s) && { "aria-hidden": "true" },
		...s
	}, [...o.map(([e, t]) => (0, d.createElement)(e, t)), ...Array.isArray(a) ? a : [a]]);
}), ee = (e, t) => {
	let n = (0, d.forwardRef)(({ className: n, ...r }, i) => (0, d.createElement)(T, {
		ref: i,
		iconNode: t,
		className: _(`lucide-${v(b(e))}`, `lucide-${e}`, n),
		...r
	}));
	return n.displayName = b(e), n;
}, te = ee("file-user", [
	["path", {
		d: "M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z",
		key: "1oefj6"
	}],
	["path", {
		d: "M14 2v5a1 1 0 0 0 1 1h5",
		key: "wfsgrz"
	}],
	["path", {
		d: "M16 22a4 4 0 0 0-8 0",
		key: "7a83pg"
	}],
	["circle", {
		cx: "12",
		cy: "15",
		r: "3",
		key: "g36mzq"
	}]
]), E = ee("square-kanban", [
	["rect", {
		width: "18",
		height: "18",
		x: "3",
		y: "3",
		rx: "2",
		key: "afitv7"
	}],
	["path", {
		d: "M8 7v7",
		key: "1x2jlm"
	}],
	["path", {
		d: "M12 7v4",
		key: "xawao1"
	}],
	["path", {
		d: "M16 7v9",
		key: "1hp2iy"
	}]
]), ne = ee("layout-dashboard", [
	["rect", {
		width: "7",
		height: "9",
		x: "3",
		y: "3",
		rx: "1",
		key: "10lvy0"
	}],
	["rect", {
		width: "7",
		height: "5",
		x: "14",
		y: "3",
		rx: "1",
		key: "16une8"
	}],
	["rect", {
		width: "7",
		height: "9",
		x: "14",
		y: "12",
		rx: "1",
		key: "1hutg5"
	}],
	["rect", {
		width: "7",
		height: "5",
		x: "3",
		y: "16",
		rx: "1",
		key: "ldoo1y"
	}]
]), re = ee("messages-square", [["path", {
	d: "M16 10a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 14.286V4a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z",
	key: "1n2ejm"
}], ["path", {
	d: "M20 9a2 2 0 0 1 2 2v10.286a.71.71 0 0 1-1.212.502l-2.202-2.202A2 2 0 0 0 17.172 19H10a2 2 0 0 1-2-2v-1",
	key: "1qfcsi"
}]]), ie = [
	{
		page: "home",
		label: "项目总览",
		icon: ee("sparkles", [
			["path", {
				d: "M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z",
				key: "1s2grr"
			}],
			["path", {
				d: "M20 2v4",
				key: "1rf3ol"
			}],
			["path", {
				d: "M22 4h-4",
				key: "gwowj6"
			}],
			["circle", {
				cx: "4",
				cy: "20",
				r: "2",
				key: "6kqj1y"
			}]
		])
	},
	{
		page: "resume",
		label: "简历实验室",
		icon: te
	},
	{
		page: "interview",
		label: "面试训练场",
		icon: re
	},
	{
		page: "tracker",
		label: "投递看板",
		icon: E
	},
	{
		page: "agent",
		label: "求职指挥台",
		icon: ne
	}
], ae = /* @__PURE__ */ t(((e) => {
	var t = Symbol.for("react.transitional.element");
	function n(e, n, r) {
		var i = null;
		if (r !== void 0 && (i = "" + r), n.key !== void 0 && (i = "" + n.key), "key" in n) for (var a in r = {}, n) a !== "key" && (r[a] = n[a]);
		else r = n;
		return n = r.ref, {
			$$typeof: t,
			type: e,
			key: i,
			ref: n === void 0 ? null : n,
			props: r
		};
	}
	e.jsx = n, e.jsxs = n;
})), D = (/* @__PURE__ */ t(((e, t) => {
	t.exports = ae();
})))();
function oe({ activePage: e }) {
	return /* @__PURE__ */ (0, D.jsxs)("aside", {
		className: "sidebar",
		children: [
			/* @__PURE__ */ (0, D.jsxs)("button", {
				className: "brand",
				"data-page": "home",
				type: "button",
				children: [/* @__PURE__ */ (0, D.jsx)("img", {
					id: "brandLogo",
					src: "/assets/images/logo%20(2).png",
					alt: "职途AI"
				}), /* @__PURE__ */ (0, D.jsxs)("span", { children: [
					"职途",
					/* @__PURE__ */ (0, D.jsx)("br", {}),
					/* @__PURE__ */ (0, D.jsx)("strong", { children: "AI" })
				] })]
			}),
			/* @__PURE__ */ (0, D.jsx)("nav", {
				className: "nav",
				"aria-label": "主导航",
				children: ie.map(({ page: t, label: n, icon: r }) => /* @__PURE__ */ (0, D.jsxs)("button", {
					className: `nav-item${e === t ? " active" : ""}`,
					"data-page": t,
					type: "button",
					"aria-current": e === t ? "page" : void 0,
					children: [/* @__PURE__ */ (0, D.jsx)(r, { "aria-hidden": "true" }), /* @__PURE__ */ (0, D.jsx)("span", { children: n })]
				}, t))
			}),
			/* @__PURE__ */ (0, D.jsxs)("div", {
				className: "provider-mini",
				children: [/* @__PURE__ */ (0, D.jsx)("span", { id: "providerDot" }), /* @__PURE__ */ (0, D.jsxs)("div", { children: [/* @__PURE__ */ (0, D.jsx)("b", {
					id: "providerName",
					children: "本地兜底"
				}), /* @__PURE__ */ (0, D.jsx)("small", {
					id: "providerModel",
					children: "规则引擎可用"
				})] })]
			})
		]
	});
}
//#endregion
//#region frontend/src/app/job-hunter-app.tsx
function se(e) {
	return new URL(e.location.href).searchParams.get("page") || "home";
}
function O({ windowObject: e = window }) {
	let [t, n] = (0, d.useState)(() => se(e));
	return (0, d.useEffect)(() => g(e, n), [e]), /* @__PURE__ */ (0, D.jsx)(oe, { activePage: t });
}
//#endregion
//#region frontend/src/agent/agent-drawer.ts
function k(e) {
	let { state: t, byId: n, syncContext: r, loadCommandCenter: i, documentObject: a, windowObject: o } = e;
	function s(e) {
		let s = n("agentDrawer");
		if (!s || s.getAttribute("aria-hidden") === "false") return;
		let c = e?.currentTarget instanceof Element ? e.currentTarget : a.activeElement;
		t.agentDrawerOpener = c, r(), s.setAttribute("aria-hidden", "false"), n("agentLauncher")?.setAttribute("aria-expanded", "true"), n("agentDrawerBackdrop")?.classList.remove("hidden"), a.body.classList.add("agent-drawer-open"), o.requestAnimationFrame(() => {
			n("closeAgentDrawer")?.focus({ preventScroll: !0 });
		}), i();
	}
	function c() {
		let e = n("agentDrawer");
		if (!e || e.getAttribute("aria-hidden") === "true") return;
		e.setAttribute("aria-hidden", "true"), n("agentLauncher")?.setAttribute("aria-expanded", "false"), n("agentDrawerBackdrop")?.classList.add("hidden"), a.body.classList.remove("agent-drawer-open");
		let r = t.agentDrawerOpener?.isConnected ? t.agentDrawerOpener : n("agentLauncher");
		t.agentDrawerOpener = null, r instanceof HTMLElement && r.focus({ preventScroll: !0 });
	}
	function l(e) {
		let t = n("agentDrawer");
		if (!t || t.getAttribute("aria-hidden") !== "false") return;
		if (e.key === "Escape") {
			e.preventDefault(), c();
			return;
		}
		if (e.key !== "Tab") return;
		let r = [...t.querySelectorAll("button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), a[href]")].filter((e) => e.offsetParent !== null);
		if (!r.length) return;
		let i = r[0], o = r[r.length - 1];
		e.shiftKey && a.activeElement === i ? (e.preventDefault(), o.focus()) : !e.shiftKey && a.activeElement === o && (e.preventDefault(), i.focus());
	}
	return {
		open: s,
		close: c,
		handleKeydown: l
	};
}
//#endregion
//#region frontend/src/agent/agent-controller.ts
var ce = {
	"resume:analysis": "analysisResumeSelect",
	"resume:export": "exportResumeSelect",
	"resume:jd": "tailorResumeSelect",
	"resume:skills": "skillResumeSelect",
	"interview:mock": "interviewResumeSelect"
}, le = {
	home: "项目总览",
	resume: "简历实验室",
	interview: "面试训练场",
	tracker: "投递看板",
	agent: "行动指挥台"
}, ue = /* @__PURE__ */ new Set([
	"agentLauncher",
	"openAgentWorkspace",
	"openAgentWorkspaceFromHelper"
]), de = /* @__PURE__ */ new Set([
	"analysisResumeSelect",
	"exportResumeSelect",
	"tailorResumeSelect",
	"skillResumeSelect",
	"interviewResumeSelect"
]);
function A(e) {
	let { state: t, byId: n, contextualAgent: r, escapeHtml: i, escapeAttr: a, renderIcons: o, loadCommandCenter: s, documentObject: c = document, windowObject: l = window } = e, u = r.createContextStore(), d = !1;
	function f() {
		if (t.currentOpportunityWorkspace?.resume?.id) return Number(t.currentOpportunityWorkspace.resume.id);
		if (t.currentPage === "resume" && t.editingResumeId) return Number(t.editingResumeId);
		let e = ce[`${t.currentPage}:${t.currentModule}`];
		return e && Number(n(e)?.value || 0) || null;
	}
	function p() {
		return u.payload();
	}
	function m() {
		u.sync({
			module: t.currentModule ? `${t.currentPage}:${t.currentModule}` : t.currentPage,
			opportunityId: t.currentOpportunityId,
			resumeId: f()
		}), h();
	}
	function h() {
		let e = n("agentContextChips");
		if (!e) return;
		let r = p(), s = [];
		if (r.module) {
			let [e, t] = String(r.module).split(":"), n = (t ? c.querySelector(`[data-section-filter="${e}:${t}"]`) : null)?.textContent?.trim() || le[e] || e;
			s.push(["module", `模块：${n}`]);
		}
		if (r.opportunity_id) {
			let e = t.currentOpportunityWorkspace?.opportunity || t.applications.find((e) => Number(e.id) === Number(r.opportunity_id)), n = e ? `${e.company} / ${e.job_title}` : `#${r.opportunity_id}`;
			s.push(["opportunity", `机会：${n}`]);
		}
		if (r.resume_id) {
			let e = t.resumes.find((e) => Number(e.id) === Number(r.resume_id));
			s.push(["resume", `简历：${e?.title || `#${r.resume_id}`}`]);
		}
		e.innerHTML = s.length ? s.map(([e, t]) => `
        <span class="agent-context-chip">${i(t)}<button type="button" data-remove-agent-context="${e}" aria-label="移除${a(t)}上下文" title="移除上下文"><i data-lucide="x"></i></button></span>
      `).join("") : "<span class=\"agent-context-empty\">未附加上下文</span>", o();
	}
	function g(e) {
		u.remove(e), h();
	}
	let _ = k({
		state: t,
		byId: n,
		syncContext: m,
		loadCommandCenter: s,
		documentObject: c,
		windowObject: l
	});
	function v() {
		d || (d = !0, c.addEventListener("click", (e) => {
			let t = e.target;
			if (!(t instanceof Element)) return;
			let n = t.closest("#agentLauncher, #openAgentWorkspace, #openAgentWorkspaceFromHelper, #closeAgentDrawer, #agentDrawerBackdrop");
			if (n?.id && ue.has(n.id)) {
				_.open({ currentTarget: n });
				return;
			}
			if (n?.id === "closeAgentDrawer" || n?.id === "agentDrawerBackdrop") {
				_.close();
				return;
			}
			let r = t.closest("[data-remove-agent-context]");
			r?.dataset.removeAgentContext && g(r.dataset.removeAgentContext);
		}), c.addEventListener("change", (e) => {
			let t = e.target;
			t instanceof HTMLElement && de.has(t.id) && m();
		}), c.addEventListener("keydown", _.handleKeydown));
	}
	return {
		bind: v,
		currentResumeId: f,
		syncContext: m,
		renderContextChips: h,
		removeContext: g,
		contextPayload: p,
		openDrawer: _.open,
		closeDrawer: _.close,
		handleDrawerKeydown: _.handleKeydown
	};
}
//#endregion
//#region frontend/src/agent/agent-result-focus.ts
function j(e) {
	let { request: t, ui: n, contextualAgent: r, windowObject: i = window, documentObject: a = document } = e, o = (e) => n.byId(e);
	function s(e, t, i) {
		let a = {
			action: "行动",
			profile: "求职目标",
			report: "求职报告"
		}, s = o(e === "profile" ? "agentResultFocus" : "agentActiveActions");
		if (s) {
			if (s.classList.remove("hidden"), i.status === "located") {
				let o = i.entity || {};
				e === "profile" ? s.innerHTML = r.profileResultHtml(i.entity) : s.insertAdjacentHTML("afterbegin", `
          <div class="command-row is-result-highlight" id="focusedAgentResult" tabindex="-1"><span><b>${n.escapeHtml(o.title || a[e])}</b><small>已验证 ${n.escapeHtml(a[e])} #${t}</small></span></div>`);
			} else {
				let r = i.status === "missing" ? "结果不存在或已失效" : "结果暂时无法读取";
				s.insertAdjacentHTML("afterbegin", `
        <div class="command-empty" id="focusedAgentResult" tabindex="-1" role="status"><b>${r}</b><span>${n.escapeHtml(a[e])} #${t}</span>${i.retry ? "<button type=\"button\" class=\"ghost small\" data-command=\"agent-result-retry\">重试</button>" : ""}</div>`);
			}
			o("focusedAgentResult")?.focus({ preventScroll: !0 });
		}
	}
	async function c() {
		let e = new URLSearchParams(i.location.search), c = [
			"resume",
			"action",
			"profile",
			"report"
		].find((t) => e.has(t));
		if (!c) return;
		let l = Number(e.get(c));
		if (!Number.isInteger(l) || l <= 0) return;
		if (o("focusedAgentResult")?.remove(), o("agentResultFocus")?.classList.add("hidden"), c === "resume") {
			let e = a.querySelector(`[data-resume-id="${l}"]`);
			if (!e) {
				n.toast("结果简历不存在或已归档");
				return;
			}
			e.classList.add("is-result-highlight"), e.focus({ preventScroll: !0 }), e.scrollIntoView({
				block: "center",
				behavior: "smooth"
			});
			return;
		}
		if (c === "action") {
			let e;
			try {
				let n = await t("/action-items"), r = n.success ? (n.data || []).find((e) => Number(e.id) === l) : null;
				e = r ? {
					success: !0,
					data: r
				} : {
					success: !1,
					http_status: n.http_status || 404
				};
			} catch (e) {
				s(c, l, r.resultLookupState(l, null, e));
				return;
			}
			let i = r.resultLookupState(l, e), a = i.entity;
			if (a) {
				o("agentActiveActions")?.insertAdjacentHTML("afterbegin", `
          <div class="command-row is-result-highlight" tabindex="-1" id="focusedAgentResult"><span><b>${n.escapeHtml(a.title)}</b><small>${n.escapeHtml(a.status || "pending")} · 行动 #${l}</small></span></div>`), o("focusedAgentResult")?.focus({ preventScroll: !0 });
				return;
			}
			s(c, l, i);
			return;
		}
		let u = c === "profile" ? `/profile/${l}` : `/career-reports/${l}`, d;
		try {
			d = await t(u);
		} catch (e) {
			s(c, l, r.resultLookupState(l, null, e));
			return;
		}
		s(c, l, r.resultLookupState(l, d));
	}
	return { focusFromLocation: c };
}
//#endregion
//#region frontend/src/agent/agent-workspace.ts
function fe(e) {
	let { userId: t, conversationStorageKey: n, state: r, request: i, ui: a, contextualAgent: o, contextPayload: s, openDrawer: c, closeDrawer: l, navigate: u, loadResumes: d, loadApplications: f, loadDashboard: p, loadOpportunityWorkspace: m, syncAgentContext: h, storage: g = localStorage, windowObject: _ = window, documentObject: v = document } = e, y = (e) => a.byId(e), { escapeHtml: b, renderIcons: x, renderText: S, toast: C, withLoading: w } = a, T = o.createConversationEpoch(), ee = o.createLatestRequestGate(), te = j({
		request: i,
		ui: a,
		contextualAgent: o,
		windowObject: _,
		documentObject: v
	});
	async function E() {
		let e = ee.begin("command-center"), t = r.agentProposalMutationEpoch, n;
		try {
			n = await i("/agent/actions");
		} catch {
			n = {
				success: !1,
				actions: []
			};
		}
		if (!ee.isCurrent(e, "command-center") || t !== r.agentProposalMutationEpoch) return;
		let a = n.success && n.actions || [];
		r.agentCommandProposalIds.forEach((e) => {
			r.agentConversationProposalIds.has(e) || r.agentProposals.delete(e);
		});
		let o = a.map((e) => fe(e, t)).filter((e) => e?.status === "pending");
		r.agentCommandProposalIds = new Set(o.map((e) => Number(e.id))), ne(o, n.success ? "" : "待确认操作暂时无法加载"), re();
	}
	function ne(e, t = "") {
		let n = y("agentActiveActions"), r = e.length;
		if (y("agentActionCount").textContent = String(r), y("agentLauncherBadge").textContent = String(r), y("agentLauncherBadge").classList.toggle("hidden", !r), n) {
			if (t) {
				n.innerHTML = `<div class="command-empty" role="alert">${b(t)}<button type="button" class="ghost small" data-command="agent-command-retry">重试</button></div>`;
				return;
			}
			n.innerHTML = r ? e.map((e) => `
    <button type="button" class="command-row" data-command="agent-proposal-open" data-proposal-id="${Number(e.id)}">
      <span><b>${b(e.preview || "待确认操作")}</b><small>${b(e.risk_level === "high" ? "高风险" : e.risk_level === "medium" ? "需确认" : "低风险")}</small></span>
      <i data-lucide="arrow-right"></i>
    </button>`).join("") : "<div class=\"command-empty\"><b>没有待确认操作</b><span>Agent 提出的写入动作会先出现在这里。</span></div>", x();
		}
	}
	function re() {
		let e = y("agentCommandOpportunities");
		if (!e) return;
		let t = r.applications.filter((e) => o.isActiveOpportunity(e.status, r.applicationStatuses)).slice(0, 6);
		e.innerHTML = t.length ? t.map((e) => `
    <button type="button" class="command-row" data-command="agent-opportunity-open" data-opportunity-id="${Number(e.id)}">
      <span><b>${b(e.company || "未命名公司")} / ${b(e.job_title || "目标岗位")}</b><small>${b(e.needs_status_review ? "待确认" : e.status || "未设置")}</small></span>
      <i data-lucide="panel-right-open"></i>
    </button>`).join("") : "<div class=\"command-empty\"><b>暂无活跃机会</b><span>在投递看板添加机会后，会同步到这里。</span></div>", x();
	}
	function ie(e, t = null) {
		c({ currentTarget: t || y("agentLauncher") });
		let n = y("chatLog").querySelector(`[data-proposal-id="${Number(e)}"]`);
		if (n) return n.scrollIntoView({
			block: "center",
			behavior: "smooth"
		});
		let i = r.agentProposals.get(Number(e));
		i && oe("这项操作需要你的确认。", "bot", { proposals: [i] });
	}
	async function ae(e = "", t = {}) {
		let a = y("agentInput"), c = typeof e == "string" && e.trim(), l = o.outboundMessage(e, a?.value || "");
		if (!l) return;
		r.agentConversationId || await k();
		let u = r.agentConversationId;
		if (!u) return;
		T.invalidate(), oe(l, "user"), c || (a.value = "");
		let d = {
			...o.chatPayload(l, u, {
				...s(),
				...t
			}),
			conversation_id: u
		}, f = await w(() => i("/agent/chat", {
			method: "POST",
			body: d
		}), "求职 Agent 正在读取上下文并处理任务...");
		if (!(r.agentConversationId !== u || f.success && f.conversation_id !== u)) {
			if (!f.success) return C(f.message || "求职 Agent 暂时不可用");
			g.setItem(n, u), oe(f.reply || f.message || "我暂时没想好，换个问法试试。", "bot", {
				proposals: f.action_proposals || [],
				inputRequest: f.input_request || {}
			}), Ce(f.events || [], f.status), we(f.suggested_actions || []), await O(u, !1), await E();
		}
	}
	async function D() {
		y("agentInput").value = "结合我的简历、面试和投递数据，生成一份求职作战报告", await ae();
	}
	function oe(e, t, n = {}) {
		let r = v.createElement("div");
		r.className = `message ${t}`, r.innerHTML = S(e), y("chatLog").appendChild(r), A(n.proposals || [], r), se(n.inputRequest || {}, r), y("chatLog").scrollTop = y("chatLog").scrollHeight;
	}
	function se(e, t) {
		if (!t || !o) return;
		let n = o.inputRequestHtml(e);
		n && t.insertAdjacentHTML("beforeend", n);
	}
	async function O(e = "", a = !0) {
		let o = await i(`/agent/conversations/${t}`);
		if (!o.success) return;
		let s = o.conversations || [];
		if (!s.length) {
			await k();
			return;
		}
		let c = e || r.agentConversationId || g.getItem(n);
		r.agentConversationId = s.some((e) => e.id === c) ? c : s[0].id, g.setItem(n, r.agentConversationId);
		let l = y("agentConversationSelect");
		l.innerHTML = s.map((e) => `<option value="${b(e.id)}">${b(e.title || "新对话")}</option>`).join(""), l.value = r.agentConversationId, a && await le();
	}
	async function k() {
		let e = await i("/agent/conversations", {
			method: "POST",
			body: {
				user_id: t,
				title: "新对话"
			}
		});
		if (!e.success) return C(e.message || "新建会话失败");
		T.invalidate(), r.agentConversationId = e.conversation.id, g.setItem(n, r.agentConversationId), await O(r.agentConversationId, !1), Se(), y("agentInput")?.focus();
	}
	async function ce() {
		if (!r.agentConversationId || !confirm("确定清空当前求职 Agent 会话吗？其他会话和求职数据不会受影响。")) return;
		let e = await i(`/agent/conversations/${r.agentConversationId}/clear`, {
			method: "POST",
			body: { user_id: t }
		});
		if (!e.success) return C(e.message || "清空失败");
		T.invalidate(), Se(), C("当前会话已清空");
	}
	async function le() {
		let e = r.agentConversationId;
		if (!e) return T.invalidate(), Se();
		let n = T.begin(e), a;
		try {
			a = await i(`/agent/conversations/${e}/messages?user_id=${t}`);
		} catch {
			a = {
				success: !1,
				messages: []
			};
		}
		if (!T.isCurrent(n, r.agentConversationId)) return;
		if (!a.success || !a.messages?.length) return Se();
		let s = [];
		for (let e of a.messages) {
			let t = e.role === "assistant" ? await ue(o.proposalsFromMetadata(e.metadata)) : [];
			if (!T.isCurrent(n, r.agentConversationId)) return;
			s.push({
				message: e,
				proposals: t
			});
		}
		if (T.isCurrent(n, r.agentConversationId)) {
			r.agentConversationProposalIds.forEach((e) => {
				r.agentCommandProposalIds.has(e) || r.agentProposals.delete(e);
			}), r.agentConversationProposalIds = new Set(s.flatMap(({ proposals: e }) => e.map((e) => Number(e.id)))), y("chatLog").innerHTML = "";
			for (let { message: e, proposals: t } of s) oe(e.content, e.role === "user" ? "user" : "bot", {
				proposals: t,
				inputRequest: e.metadata?.input_request || {}
			}), e.role === "assistant" && (Ce(e.metadata?.events || [], e.metadata?.status || "completed"), we(e.metadata?.suggested_actions || []));
		}
	}
	async function ue(e) {
		return Promise.all(e.map(de));
	}
	async function de(e) {
		let t;
		try {
			t = await i(`/agent/actions/${Number(e.id)}`);
		} catch (t) {
			return o.unavailableProposal(e, o.hydrationFailureKind(null, t));
		}
		return t.success ? o.authoritativeHydrationSuccess(t.action) : o.unavailableProposal(e, o.hydrationFailureKind(t));
	}
	function A(e, t) {
		!t || !e.length || e.forEach((e) => {
			r.agentConversationProposalIds.add(Number(e.id));
			let n = fe(e, r.agentProposalMutationEpoch);
			t.insertAdjacentHTML("beforeend", o.proposalHtml(n));
		});
	}
	function fe(e, t = r.agentProposalMutationEpoch) {
		let n = Number(e?.id);
		if (!Number.isInteger(n) || n <= 0) return e;
		let i = r.agentProposals.get(n), a = r.agentProposalEpochs.get(n) || 0, s = o.mergeProposalState(i, e, {
			currentEpoch: a,
			incomingEpoch: t
		});
		return s !== i && (r.agentProposals.set(n, s), r.agentProposalEpochs.set(n, Math.max(a, t))), s;
	}
	function pe() {
		return r.agentProposalMutationEpoch += 1, T.invalidate(), r.agentProposalMutationEpoch;
	}
	function me(e, t) {
		return e?.error?.message || e?.message || t;
	}
	function he(e, t) {
		let n = {};
		return e.querySelectorAll("[data-agent-edit-field]").forEach((e) => {
			let r = e.dataset.agentEditField.split("."), i = r.reduce((e, t) => e?.[t], t.editable), a = e.value;
			if (typeof i == "number" && (a = Number(a)), Array.isArray(i)) try {
				a = JSON.parse(a);
			} catch {
				a = e.value.split(",").map((e) => e.trim()).filter(Boolean);
			}
			let o = n;
			r.forEach((e, t) => {
				t === r.length - 1 ? o[e] = a : o = o[e] ||= {};
			});
		}), n;
	}
	function ge(e, t, n = r.agentProposalMutationEpoch) {
		let i = fe(t, n);
		return e.outerHTML = o.proposalHtml(i), x(), i;
	}
	async function _e(e) {
		let t = e.target.closest("[data-agent-navigation]");
		if (t) {
			let e = o.normalizedSuggestedActions([{
				label: t.textContent || "下一步",
				page: t.dataset.agentPage,
				module: t.dataset.agentModule
			}]);
			e[0] && (l(), u(e[0].page, e[0].module));
			return;
		}
		let n = e.target.closest("[data-agent-resume-choice]");
		if (n) {
			let e = Number(n.dataset.agentResumeChoice), t = [
				"revision",
				"analysis",
				"interview_questions"
			].includes(n.dataset.agentWorkflow) ? n.dataset.agentWorkflow : "analysis", r = o.selectionMessage({ workflow: t }, {
				id: e,
				label: n.dataset.agentResumeLabel
			});
			r && await ae(r, { resume_id: e });
			return;
		}
		await be(e);
	}
	async function ve(e, t) {
		let n = e.querySelector(".agent-draft-editor");
		if (n) return n.scrollIntoView({
			block: "nearest",
			behavior: "smooth"
		});
		let r;
		try {
			r = await i(`/agent/actions/${Number(t.id)}/draft`);
		} catch {
			C("草稿暂时无法加载，请重试");
			return;
		}
		if (!r.success || !r.draft) {
			C(me(r, "草稿暂时无法加载"));
			return;
		}
		let a = r.draft, o = v.createElement("section");
		o.className = "agent-draft-editor", o.innerHTML = "<header><b>版本草稿</b><small>确认前可编辑；保存后会新建版本，不覆盖原简历。</small></header>";
		let s = v.createElement("textarea");
		s.className = "input textarea agent-draft-content", s.rows = 12, s.value = String(a.content || ""), s.setAttribute("aria-label", "可编辑的简历版本草稿");
		let c = v.createElement("div");
		c.className = "proposal-controls";
		let l = v.createElement("button");
		l.type = "button", l.className = "ghost", l.dataset.agentAction = "save-draft", l.textContent = "保存草稿修改", c.appendChild(l), o.append(s, c), e.appendChild(o), s.focus({ preventScroll: !0 });
	}
	async function ye(e, t) {
		let n = e.querySelector(".agent-draft-content"), r = String(n?.value || "").trim();
		if (!r) return C("草稿正文不能为空");
		let a = e.querySelector("[data-agent-action=\"save-draft\"]");
		a && (a.disabled = !0);
		try {
			let e = await i(`/agent/actions/${Number(t.id)}/edit`, {
				method: "POST",
				body: { content: r }
			});
			if (!e.success) return C(me(e, "草稿保存失败，请重试"));
			fe(e.action, pe()), C("草稿已更新，确认后才会保存为新版本");
		} catch {
			C("网络连接失败，草稿未保存");
		} finally {
			a && (a.disabled = !1);
		}
	}
	async function be(e) {
		let t = e.target.closest("[data-agent-action]");
		if (!t) return;
		let n = t.closest("[data-proposal-id]"), a = Number(n?.dataset.proposalId), s = t.dataset.agentAction, c = r.agentProposals.get(a);
		if (n && c && s === "open-draft") {
			await ve(n, c);
			return;
		}
		if (n && c && s === "save-draft") {
			await ye(n, c);
			return;
		}
		if (n && c && s === "retry-hydration") {
			let e = pe(), t = c.hydrationSource || c;
			ge(n, {
				...c,
				hydrationRetry: !1,
				busy: !0
			}, e);
			let r = await de(t), i = y("chatLog").querySelector(`[data-proposal-id="${a}"]`);
			i && ge(i, r, e);
			return;
		}
		if (!n || !c || c.status !== "pending") return;
		let l = pe(), u = s === "edit" ? he(n, c) : {}, d = `${s}_start`, f = o.transitionProposal(c, d);
		ge(n, f, l);
		try {
			let e = await i(`/agent/actions/${a}/${s}`, {
				method: "POST",
				body: u
			}), t = y("chatLog").querySelector(`[data-proposal-id="${a}"]`);
			if (!e.success) {
				f = o.transitionProposal(f, `${s}_error`, { error: me(e, "操作失败，请重试") }), t && ge(t, f, l);
				return;
			}
			let n = pe();
			f = o.transitionProposal(f, `${s}_success`, { action: e.action }), t && ge(t, f, n);
			let r = E();
			s === "confirm" ? (await xe(f.result), C("操作已确认并完成")) : C(s === "cancel" ? "操作已取消，业务数据未改变" : "预览已更新，请确认后执行"), await r;
		} catch {
			let e = y("chatLog").querySelector(`[data-proposal-id="${a}"]`);
			f = o.transitionProposal(f, `${s}_error`, { error: "网络连接失败，请重试" }), e && ge(e, f, l);
		}
	}
	async function xe(e) {
		let t = r.currentOpportunityId;
		await Promise.all([
			d(),
			f(),
			p()
		]), t && await m(t, { isCurrent: () => !0 }), h();
	}
	function Se() {
		r.agentConversationProposalIds.forEach((e) => {
			r.agentCommandProposalIds.has(e) || r.agentProposals.delete(e);
		}), r.agentConversationProposalIds = /* @__PURE__ */ new Set(), y("chatLog").innerHTML = "", oe("你好，我是你的求职 Agent。无需 API Key 也能读取本地求职数据、诊断当前进度并安排下一步；配置模型后还可以处理更开放的问题。", "bot");
	}
	function Ce(e, t = "completed") {
		if (!e.length && t === "completed") return;
		let n = {
			list_resumes: "读取简历列表",
			get_resume: "读取简历正文",
			analyze_resume: "分析简历",
			diagnose_resume: "本地诊断简历",
			prepare_resume_revision: "生成可编辑草稿",
			propose_career_action: "创建待确认操作",
			match_job: "匹配目标岗位",
			analyze_jd: "解析岗位 JD",
			get_interview_question: "获取面试题",
			generate_resume_interview_questions: "生成定制面试题",
			evaluate_answer: "评估面试回答",
			list_applications: "读取投递记录",
			get_dashboard: "读取求职看板",
			get_career_profile: "读取职业目标",
			list_action_items: "读取行动项",
			get_training_insights: "汇总训练记录",
			generate_career_report: "汇总求职报告",
			web_search: "搜索公开信息",
			fetch_webpage: "读取公开网页"
		}, r = e.map((e) => `
    <span class="agent-event ${e.status === "success" ? "is-success" : "is-error"}">
      <i data-lucide="${e.status === "success" ? "check" : "triangle-alert"}"></i>
      ${b(n[e.name] || e.name)}
    </span>
  `).join(""), i = t === "degraded" ? "本地执行" : t === "needs_input" ? "选择简历后继续" : "任务记录";
		y("chatLog").lastElementChild?.insertAdjacentHTML("beforeend", `<div class="agent-events"><small>${i}</small>${r}</div>`), x();
	}
	function we(e) {
		let t = o.suggestedActionsHtml(e);
		t && (y("chatLog").lastElementChild?.insertAdjacentHTML("beforeend", t), x());
	}
	return {
		loadCommandCenter: E,
		renderCommandOpportunities: re,
		openProposal: ie,
		sendMessage: ae,
		generateCareerReport: D,
		loadConversations: O,
		createConversation: k,
		clearConversation: ce,
		handleChatLogClick: _e,
		focusResultFromLocation: te.focusFromLocation
	};
}
//#endregion
//#region frontend/src/agent/contextual-agent.mjs
var pe = /* @__PURE__ */ n({
	authoritativeHydrationSuccess: () => We,
	chatPayload: () => De,
	createContextStore: () => xe,
	createConversationEpoch: () => Ce,
	createLatestRequestGate: () => Se,
	escapeHtml: () => M,
	flattenEditable: () => Ne,
	hydrationFailureKind: () => Ue,
	inputRequestHtml: () => Oe,
	isActiveOpportunity: () => Ge,
	mergeProposalState: () => Ee,
	normalizedContext: () => ye,
	normalizedSuggestedActions: () => Ae,
	outboundMessage: () => be,
	profileResultHtml: () => qe,
	proposalHtml: () => Fe,
	proposalsFromMetadata: () => Me,
	resultHref: () => Ve,
	resultLookupState: () => Ke,
	resultRoute: () => Be,
	selectionMessage: () => ke,
	suggestedActionsHtml: () => je,
	transitionProposal: () => Ie,
	unavailableProposal: () => He
}), me = {
	module: "module",
	opportunity: "opportunity_id",
	resume: "resume_id"
}, he = {
	home: /* @__PURE__ */ new Set([""]),
	resume: /* @__PURE__ */ new Set([
		"input",
		"manage",
		"analysis",
		"export",
		"jd",
		"skills"
	]),
	interview: /* @__PURE__ */ new Set([
		"mock",
		"professional",
		"practice",
		"records"
	]),
	tracker: /* @__PURE__ */ new Set([
		"add",
		"board",
		"salary"
	]),
	agent: /* @__PURE__ */ new Set([""])
}, ge = {
	career_direction: "求职方向",
	target_role: "目标岗位",
	cities: "目标城市",
	"salary.min": "期望薪资下限",
	"salary.max": "期望薪资上限",
	experience: "经验要求",
	confirmed_skills: "已确认技能",
	company: "公司",
	job_title: "岗位",
	status: "阶段",
	city: "城市",
	salary_min: "薪资下限",
	salary_max: "薪资上限",
	priority: "优先级",
	channel: "投递渠道",
	source_url: "岗位链接",
	next_action_at: "下次跟进时间",
	interview_at: "面试时间",
	deadline_at: "截止时间",
	title: "标题",
	type: "任务类型",
	description: "说明",
	due_date: "截止日期",
	due_at: "提醒时间",
	report_type: "报告类型",
	period_start: "开始日期",
	period_end: "结束日期"
}, _e = {
	career_direction: {
		tech: "技术 / 软件 / AI",
		ops: "运营 / 新媒体 / 内容",
		marketing: "市场 / 销售 / 商务",
		finance: "财务 / 会计 / 审计",
		education: "教育 / 师范 / 教培",
		hr: "行政 / 人事 / 通用职能"
	},
	status: {
		active: "启用",
		draft: "草稿",
		archived: "已归档",
		pending: "待处理",
		in_progress: "进行中",
		completed: "已完成",
		cancelled: "已取消",
		ready: "已准备"
	},
	type: {
		interview_plan: "面试准备",
		follow_up: "跟进",
		career_report: "求职报告"
	},
	report_type: {
		weekly: "周度复盘",
		monthly: "月度复盘"
	}
};
function ve(e) {
	let t = Number(e);
	return Number.isInteger(t) && t > 0 ? t : null;
}
function ye(e) {
	let t = {};
	typeof e?.module == "string" && e.module.trim() && (t.module = e.module.trim().slice(0, 100));
	let n = ve(e?.opportunity_id ?? e?.opportunityId), r = ve(e?.resume_id ?? e?.resumeId);
	return n && (t.opportunity_id = n), r && (t.resume_id = r), t;
}
function be(e, t = "") {
	return typeof e == "string" && e.trim() ? e.trim() : typeof t == "string" ? t.trim() : "";
}
function xe(e = {}) {
	let t = ye(e), n = /* @__PURE__ */ new Map();
	return {
		sync(e = {}) {
			let r = ye(e);
			return Object.entries(me).forEach(([e, i]) => {
				let a = r[i];
				if (a == null) {
					delete t[i], n.delete(e);
					return;
				}
				if (n.get(e) === String(a)) {
					delete t[i];
					return;
				}
				n.delete(e), t[i] = a;
			}), this.payload();
		},
		remove(e) {
			let r = me[e];
			return r ? (t[r] != null && n.set(e, String(t[r])), delete t[r], this.payload()) : this.payload();
		},
		payload() {
			return { ...t };
		}
	};
}
function Se() {
	let e = 0;
	return {
		begin(t = "") {
			return e += 1, {
				generation: e,
				identity: String(t)
			};
		},
		isCurrent(t, n = "") {
			return !!(t && t.generation === e && t.identity === String(n));
		},
		invalidate() {
			e += 1;
		}
	};
}
function Ce() {
	return Se();
}
var we = /* @__PURE__ */ new Set([
	"completed",
	"cancelled",
	"expired",
	"failed"
]);
function Te(e) {
	let t = e?.revision == null ? NaN : Number(e.revision);
	if (Number.isFinite(t)) return t;
	let n = Date.parse(e?.updated_at || "");
	return Number.isFinite(n) ? n : null;
}
function Ee(e, t, n = {}) {
	if (!e) return t;
	if (!t || ve(e.id) !== ve(t.id) || we.has(String(e.status)) && !we.has(String(t.status))) return e;
	let r = Number(n.currentEpoch) || 0;
	if ((Number(n.incomingEpoch) || 0) < r) return e;
	let i = Te(e), a = Te(t);
	return i !== null && a !== null && a < i ? e : {
		...e,
		...t
	};
}
function De(e, t, n = {}) {
	let r = {
		conversation_id: String(t || ""),
		message: String(e || "")
	}, i = ye(n);
	return Object.keys(i).length && (r.context = i), r;
}
function M(e = "") {
	return String(e).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
function Oe(e) {
	if (!e || e.kind !== "resume_select" || !Array.isArray(e.options)) return "";
	let t = [
		"revision",
		"analysis",
		"interview_questions"
	].includes(e.workflow) ? e.workflow : "analysis", n = e.options.filter((e) => ve(e?.id)).map((e) => `
      <button type="button" class="agent-resume-choice" data-agent-resume-choice="${ve(e.id)}" data-agent-resume-label="${M(e.label || "简历")}" data-agent-workflow="${t}">
        <b>${M(e.label || `简历 #${e.id}`)}</b>
        ${e.preview ? `<small>${M(e.preview)}</small>` : ""}
        <span>${t === "revision" ? "生成优化草稿" : t === "interview_questions" ? "生成定制面试题" : "开始诊断"}</span>
      </button>
    `).join("");
	return n ? `<section class="agent-input-request" data-agent-input-kind="resume_select">
      <p>${M(e.prompt || "选择一份简历")}</p>
      <div class="agent-resume-choice-list">${n}</div>
    </section>` : "";
}
function ke(e, t) {
	if (!ve(t?.id ?? t)) return "";
	let n = e?.workflow === "revision" ? "生成优化草稿" : e?.workflow === "interview_questions" ? "生成定制面试题" : "进行简历诊断", r = typeof t?.label == "string" ? t.label.trim().slice(0, 80) : "";
	return r ? `已选择「${r}」，请${n}` : `已选择这份简历，请${n}`;
}
function Ae(e) {
	if (!Array.isArray(e)) return [];
	let t = /* @__PURE__ */ new Set();
	return e.flatMap((e) => {
		let n = typeof e?.label == "string" ? e.label.trim().slice(0, 80) : "", r = typeof e?.page == "string" ? e.page : "", i = typeof e?.module == "string" ? e.module : "";
		if (!n || !he[r]?.has(i)) return [];
		let a = `${r}:${i}`;
		return t.has(a) ? [] : (t.add(a), [{
			label: n,
			page: r,
			module: i
		}]);
	}).slice(0, 3);
}
function je(e) {
	let t = Ae(e).map((e) => `
      <button type="button" data-agent-navigation data-agent-page="${M(e.page)}" data-agent-module="${M(e.module)}">
        ${M(e.label)}<i data-lucide="arrow-right"></i>
      </button>
    `).join("");
	return t ? `<div class="agent-suggested-actions">${t}</div>` : "";
}
function Me(e) {
	return Array.isArray(e?.action_proposals) ? e.action_proposals.filter((e) => e && ve(e.id) && typeof e.status == "string") : [];
}
function Ne(e, t = "") {
	return !e || typeof e != "object" || Array.isArray(e) ? [] : Object.entries(e).flatMap(([e, n]) => {
		let r = t ? `${t}.${e}` : e;
		return n && typeof n == "object" && !Array.isArray(n) ? Ne(n, r) : [{
			path: r,
			value: n
		}];
	});
}
function Pe(e) {
	return e?.action_type === "create_resume_version" ? [] : Ne(e?.editable).flatMap(({ path: e, value: t }) => {
		let n = ge[e];
		if (!n) return [];
		let r = _e[e]?.[t];
		return [{
			path: e,
			label: n,
			value: t,
			serialized: Array.isArray(t) ? t.join("、") : r ?? t ?? ""
		}];
	});
}
function Fe(e) {
	let t = String(e?.status || "unknown"), n = t === "pending", r = !!e?.busy, i = Pe(e).map(({ path: e, label: t, value: i, serialized: a }) => {
		let o = typeof i == "number" ? "number" : "text";
		return `<label class="agent-edit-field"><span>${M(t)}</span><input class="input" type="${o}" data-agent-edit-field="${M(e)}" value="${M(a)}" ${n && !r ? "" : "disabled"}></label>`;
	}).join(""), a = n && e?.action_type === "create_resume_version" ? `<button type="button" class="ghost" data-agent-action="open-draft" ${r ? "disabled" : ""}>查看并编辑草稿</button>` : "", o = n ? `
      <div class="proposal-controls">
        ${a}
        ${i ? `<button type="button" class="ghost" data-agent-action="edit" ${r ? "disabled" : ""}>保存修改</button>` : ""}
        <button type="button" class="primary" data-agent-action="confirm" ${r ? "disabled" : ""}>确认执行</button>
        <button type="button" class="ghost" data-agent-action="cancel" ${r ? "disabled" : ""}>取消</button>
      </div>` : e?.hydrationRetry ? "\n      <div class=\"proposal-controls\"><button type=\"button\" class=\"ghost\" data-agent-action=\"retry-hydration\">重试加载</button></div>" : "", s = e?.result?.id ? `<a class="proposal-result-link" href="${M(Ve(e.result))}" data-agent-result-link>${M(ze(e.result))}</a>` : "";
	return `<article class="agent-proposal" data-proposal-id="${M(e?.id || "")}" data-status="${M(t)}">
      <header><span class="proposal-status">${M(Le(t))}</span><span class="proposal-risk risk-${M(e?.risk_level || "low")}">${M(Re(e?.risk_level))}</span></header>
      <p>${M(e?.preview || "待确认操作")}</p>
      ${i ? `<div class="proposal-fields">${i}</div>` : ""}
      ${e?.error ? `<div class="proposal-error" role="alert">${M(e.error)}</div>` : ""}
      ${s}${o}
    </article>`;
}
function Ie(e, t, n = {}) {
	let r = {
		...e,
		error: ""
	};
	return t === "confirm_start" || t === "cancel_start" || t === "edit_start" ? {
		...r,
		busy: !0
	} : t.endsWith("_error") ? {
		...r,
		busy: !1,
		error: String(n.error || "操作失败，请重试")
	} : t.endsWith("_success") && n.action ? {
		...r,
		...n.action,
		busy: !1,
		error: ""
	} : r;
}
function Le(e) {
	return {
		pending: "等待确认",
		executing: "执行中",
		completed: "已完成",
		cancelled: "已取消",
		expired: "已过期",
		failed: "执行失败",
		stale: "提案不可用",
		forbidden: "无权访问",
		unavailable: "暂时无法加载"
	}[e] || "状态未知";
}
function Re(e) {
	return {
		low: "低风险",
		medium: "需确认",
		high: "高风险"
	}[e] || "需确认";
}
function ze(e) {
	return {
		opportunity: "查看机会",
		resume: "查看简历",
		action_item: "查看行动",
		career_profile: "查看目标",
		career_report: "查看报告"
	}[e?.entity_type] || "查看结果";
}
function Be(e) {
	let t = ve(e?.id);
	if (!t) return null;
	let n = {
		opportunity: {
			page: "tracker",
			module: "board",
			key: "opportunity"
		},
		resume: {
			page: "resume",
			module: "manage",
			key: "resume"
		},
		action_item: {
			page: "agent",
			module: null,
			key: "action"
		},
		career_profile: {
			page: "home",
			module: null,
			key: "profile"
		},
		career_report: {
			page: "agent",
			module: null,
			key: "report"
		}
	};
	return n[e.entity_type] ? {
		...n[e.entity_type],
		id: t
	} : null;
}
function Ve(e) {
	let t = Be(e);
	if (!t) return "?page=home";
	let n = new URLSearchParams({ page: t.page });
	return t.module && n.set("module", t.module), n.set(t.key, String(t.id)), `?${n.toString()}`;
}
function He(e, t) {
	let n = {
		not_found: "stale",
		forbidden: "forbidden",
		server: "unavailable",
		network: "unavailable"
	}, r = {
		not_found: "该提案已不存在，不能继续操作。",
		forbidden: "该提案不属于当前用户，不能继续操作。",
		server: "提案状态暂时无法读取，请重试。",
		network: "网络连接失败，无法确认提案最新状态。"
	};
	return {
		...e,
		status: n[t] || "unavailable",
		editable: {},
		error: r[t] || r.server,
		hydrationRetry: t === "server" || t === "network",
		hydrationSource: e
	};
}
function Ue(e, t = null) {
	return t ? "network" : e?.http_status === 404 ? "not_found" : e?.http_status === 403 ? "forbidden" : "server";
}
function We(e) {
	return !e || typeof e != "object" ? e : {
		...e,
		busy: !1,
		error: "",
		hydrationRetry: !1,
		hydrationSource: null
	};
}
function Ge(e, t = []) {
	return e === "已结束" || e === "已拒绝" ? !1 : e === "Offer" || !t.includes(e) || t.includes(e);
}
function Ke(e, t, n = null) {
	if (n || !t || !t.success && t.http_status !== 404) return {
		status: "unavailable",
		retry: !0,
		entity: null
	};
	let r = t.success && ve(t.data?.id) === ve(e) ? t.data : null;
	return r ? {
		status: "located",
		retry: !1,
		entity: r
	} : {
		status: "missing",
		retry: !1,
		entity: null
	};
}
function qe(e) {
	let t = ve(e?.id);
	if (!t) return "";
	let n = typeof e.target_role == "string" && e.target_role.trim() ? e.target_role.trim() : "未设置", r = Array.isArray(e.cities) ? e.cities.map((e) => String(e).trim()).filter(Boolean).join("、") : "", i = e.salary && typeof e.salary == "object" && !Array.isArray(e.salary) ? [e.salary.min, e.salary.max].filter((e) => e != null && e !== "").join(" - ") : "";
	return `<article class="profile-result-summary is-result-highlight" id="focusedAgentResult" data-profile-id="${t}" tabindex="-1">
      <header><b>求职画像 #${t}</b><small>已验证 Agent 结果</small></header>
      <dl>
        <div><dt>目标岗位</dt><dd>${M(n)}</dd></div>
        <div><dt>目标城市</dt><dd>${M(r || "未设置")}</dd></div>
        <div><dt>期望薪资</dt><dd>${M(i || "未设置")}</dd></div>
      </dl>
    </article>`;
}
//#endregion
//#region frontend/src/career/career-form.mjs
var Je = /* @__PURE__ */ n({
	hydrateProfile: () => Qe,
	loadProfile: () => $e,
	parseList: () => Ye,
	resolveDirection: () => Ze,
	saveProfile: () => et,
	serializeList: () => Xe
});
function Ye(e) {
	let t = /* @__PURE__ */ new Set();
	return String(e || "").split(/[,，、;；\n]/).map((e) => e.trim()).filter((e) => !e || t.has(e) ? !1 : (t.add(e), !0));
}
function Xe(e) {
	return Ye(Array.isArray(e) ? e.join("；") : e).join("；");
}
function Ze(e, t, n) {
	let r = String(e || "").trim(), i = new Set((t || []).map(String)), a = !!(r && i.has(r));
	return {
		value: a ? r : n,
		matched: a,
		requested: r
	};
}
function Qe(e, t, n) {
	let r = Ze(e.career_direction, Array.from(t.direction?.options || [], (e) => e.value), t.direction?.value || n.careerProfile);
	t.role.value = e.target_role || "", t.cities.value = Xe(e.cities || []), t.salaryMin.value = e.salary?.min ?? "", t.salaryMax.value = e.salary?.max ?? "", t.skills.value = Xe(e.confirmed_skills || []), r.matched && (t.direction.value = r.value, n.careerProfile = r.value);
	let i = e.target_role || "未设置目标岗位";
	return t.status.textContent = r.requested && !r.matched ? `已载入目标档案：${i}（档案方向 ${r.requested} 暂无可选项，保留当前方向）` : `已载入目标档案：${i}`, { direction: r };
}
async function $e({ request: e, controls: t, state: n }) {
	t.retry && (t.retry.hidden = !0);
	try {
		let r = await e();
		if (!r?.success) {
			let e = r?.message || "目标档案加载失败";
			return t.status.textContent = `${e}，请重试。当前填写内容已保留。`, t.retry && (t.retry.hidden = !1), {
				ok: !1,
				response: r
			};
		}
		return r.data ? {
			ok: !0,
			response: r,
			...Qe(r.data, t, n)
		} : (t.status.textContent = "还没有目标档案，先填写目标岗位，Agent 才能给出更贴合的建议。", t.retry && (t.retry.hidden = !0), {
			ok: !0,
			empty: !0,
			response: r,
			direction: {
				value: t.direction?.value || n.careerProfile || "",
				matched: !1,
				requested: ""
			}
		});
	} catch (e) {
		return t.status.textContent = "目标档案加载失败，请重试。当前填写内容已保留。", t.retry && (t.retry.hidden = !1), {
			ok: !1,
			error: e
		};
	}
}
async function et({ request: e, payload: t, status: n, onSuccess: r = () => {} }) {
	let i;
	try {
		i = await e(t);
	} catch (e) {
		return n.textContent = "目标档案保存失败，请重试。表单内容已保留。", {
			ok: !1,
			error: e
		};
	}
	if (!i?.success || !i.data) return n.textContent = `${i?.message || "目标档案保存失败"}，请重试。表单内容已保留。`, {
		ok: !1,
		response: i
	};
	n.textContent = `目标档案已保存：${i.data.target_role || "未设置目标岗位"}`;
	try {
		return await r(i.data), {
			ok: !0,
			response: i
		};
	} catch (e) {
		return {
			ok: !0,
			response: i,
			followupError: e
		};
	}
}
//#endregion
//#region frontend/src/interview/browser-capabilities.mjs
var tt = /* @__PURE__ */ n({
	RECORDER_FORMATS: () => nt,
	applyCapabilityUI: () => ft,
	audioFileDescriptor: () => ct,
	audioInputPlan: () => ut,
	audioPlaybackErrorMessage: () => lt,
	canRecordAudio: () => it,
	extensionForMime: () => ot,
	selectRecorderFormat: () => at,
	speechRecognition: () => rt,
	startSpeechSafely: () => pt
}), nt = Object.freeze([
	Object.freeze({
		mimeType: "audio/webm;codecs=opus",
		extension: "webm"
	}),
	Object.freeze({
		mimeType: "audio/webm",
		extension: "webm"
	}),
	Object.freeze({
		mimeType: "audio/ogg;codecs=opus",
		extension: "ogg"
	}),
	Object.freeze({
		mimeType: "audio/ogg",
		extension: "ogg"
	}),
	Object.freeze({
		mimeType: "audio/mp4",
		extension: "m4a"
	})
]);
function rt(e = {}) {
	return typeof e.SpeechRecognition == "function" ? {
		kind: "standard",
		Recognition: e.SpeechRecognition
	} : typeof e.webkitSpeechRecognition == "function" ? {
		kind: "webkit",
		Recognition: e.webkitSpeechRecognition
	} : {
		kind: "none",
		Recognition: null
	};
}
function it(e = {}, t = {}) {
	return typeof e.MediaRecorder == "function" && typeof t.mediaDevices?.getUserMedia == "function";
}
function at(e) {
	if (typeof e?.isTypeSupported != "function") return null;
	let t = nt.find(({ mimeType: t }) => e.isTypeSupported(t));
	return t ? { ...t } : null;
}
function ot(e = "") {
	let t = String(e).toLowerCase();
	return t.includes("mp4") || t.includes("m4a") ? "m4a" : t.includes("webm") ? "webm" : t.includes("ogg") ? "ogg" : t.includes("mpeg") || t.includes("mp3") ? "mp3" : t.includes("wav") ? "wav" : "";
}
var st = /* @__PURE__ */ new Set([
	"webm",
	"ogg",
	"m4a",
	"mp4",
	"mp3",
	"wav",
	"aac",
	"flac",
	"opus",
	"audio"
]);
function ct(e = {}) {
	let t = typeof e.type == "string" ? e.type : "", n = (typeof e.name == "string" && e.name.trim() ? e.name.trim().split(/[\\/]/).pop() : "interview-answer").replace(/[<>:"/\\|?*\u0000-\u001f]/g, "_").slice(0, 180) || "interview-answer", r = n.match(/\.([a-z0-9]{1,10})$/i), i = r?.[1].toLowerCase() || "", a = ot(t), o = a || (st.has(i) ? i : "audio"), s = r ? n.slice(0, -r[0].length) : n;
	return {
		filename: !a && st.has(i) || i === o ? n : `${s || "interview-answer"}.${o}`,
		extension: o,
		mimeType: t,
		mayNotPlay: o === "audio"
	};
}
function lt() {
	return "当前浏览器无法播放此格式，可下载原文件；文字回答仍可继续。";
}
function ut(e = {}, t = {}) {
	let n = it(e, t);
	return {
		canRecord: n,
		recorderFormat: n ? at(e.MediaRecorder) : null,
		canUpload: !0,
		canType: !0
	};
}
function dt(e, t) {
	e && (e.hidden = t, e.disabled = t, e.classList?.toggle("hidden", t), e.setAttribute?.("aria-hidden", String(t)));
}
function ft(e, t) {
	let n = (t) => e?.getElementById?.(t), r = t.speech?.kind === "none";
	dt(n("voiceBtn"), r);
	let i = n("speechCapabilityStatus");
	i && (i.textContent = r ? "当前浏览器不支持语音转文字，请直接使用文字回答。" : "语音转文字可用，文字回答始终可用。");
	let a = !t.audio?.canRecord;
	for (let e of [
		"recordAudioBtn",
		"stopAudioBtn",
		"roomRecordBtn",
		"roomStopRecordBtn"
	]) dt(n(e), a);
	let o = n("recordingCapabilityStatus");
	o && (o.textContent = a ? "当前浏览器不能直接录音，仍可上传音频或使用文字回答。" : "浏览器录音可用，也可以上传音频或使用文字回答。");
}
function pt(e) {
	try {
		return e.start(), {
			ok: !0,
			error: null
		};
	} catch (e) {
		return {
			ok: !1,
			error: e
		};
	}
}
//#endregion
//#region frontend/src/interview/interview-audio.ts
function mt(e, t) {
	let n = e(t);
	if (!n) throw Error(`Missing interview audio control: #${t}`);
	return n;
}
function ht(e, t) {
	let { userId: n, state: r, request: i, byId: a, toast: o, withLoading: s, downloadBlob: c, downloadResponse: l, media: u, capabilities: d } = e, f = u.createObjectUrlRegistry({
		create: (e) => URL.createObjectURL(e),
		revoke: (e) => URL.revokeObjectURL(e)
	});
	function p(e = "") {
		return d.extensionForMime(e);
	}
	function m(e = "interview-answer") {
		return e.replace(/\.[^.]+$/, "") || "interview-answer";
	}
	async function h(e) {
		let t = window.AudioContext || window.webkitAudioContext;
		if (!t) throw Error("当前浏览器不支持音频解码");
		let n = await u.decodeAudioBlob(e, t), r = Math.min(2, n.numberOfChannels), i = n.sampleRate, a = n.length, o = r * 2, s = a * o, c = new ArrayBuffer(44 + s), l = new DataView(c), d = (e, t) => {
			for (let n = 0; n < t.length; n += 1) l.setUint8(e + n, t.charCodeAt(n));
		};
		d(0, "RIFF"), l.setUint32(4, 36 + s, !0), d(8, "WAVE"), d(12, "fmt "), l.setUint32(16, 16, !0), l.setUint16(20, 1, !0), l.setUint16(22, r, !0), l.setUint32(24, i, !0), l.setUint32(28, i * o, !0), l.setUint16(32, o, !0), l.setUint16(34, 16, !0), d(36, "data"), l.setUint32(40, s, !0);
		let f = Array.from({ length: r }, (e, t) => n.getChannelData(t)), p = 44;
		for (let e = 0; e < a; e += 1) for (let t = 0; t < r; t += 1) {
			let n = Math.max(-1, Math.min(1, f[t][e]));
			l.setInt16(p, n < 0 ? n * 32768 : n * 32767, !0), p += 2;
		}
		return new Blob([c], { type: "audio/wav" });
	}
	async function g(e, t = "wav") {
		if (!e) {
			o("没有可下载的音频文件");
			return;
		}
		if (!i.raw) throw Error("ApiClient.raw is required for audio downloads");
		if (t === "wav") {
			try {
				let t = await i.raw(`/uploads/${encodeURIComponent(e)}`);
				if (!t.ok) throw Error("音频读取失败");
				c(await h(await t.blob()), `${m(e)}.wav`), o("WAV 音频已开始下载");
			} catch (e) {
				o(`WAV 导出失败：${e.message}`);
			}
			return;
		}
		let n = await i.raw(`/uploads/${encodeURIComponent(e)}/download/${t}`), r = t === "original" ? d.audioFileDescriptor({
			name: e,
			type: ""
		}).filename : `${m(e)}.${t}`;
		await l(n, r);
	}
	async function _(e, t = "upload", n = 0) {
		return u.computeAudioMetrics(e, {
			source: t,
			startedAt: n,
			AudioContext: window.AudioContext || window.webkitAudioContext || null
		});
	}
	function v(e = "answer") {
		let t = mt(a, e === "room" ? "roomAudioPlayback" : "audioPlayback"), n = mt(a, e === "room" ? "roomAudioMetricPreview" : "audioMetricPreview"), i = mt(a, e === "room" ? "roomAudioPlaybackStatus" : "audioPlaybackStatus"), o = mt(a, e === "room" ? "roomAudioDownloadLink" : "audioDownloadLink");
		if (r.audioBlob) {
			let n = f.replace(e, r.audioBlob), a = d.audioFileDescriptor(r.audioBlob);
			t.src = n, t.dataset.url = n, o.href = n, o.download = a.filename, o.classList.remove("hidden"), i.classList.remove("hidden", "is-warning"), i.textContent = a.mayNotPlay ? d.audioPlaybackErrorMessage() : `已载入 ${a.filename}，可回放或下载原文件。`, i.classList.toggle("is-warning", a.mayNotPlay), t.onerror = () => {
				i.textContent = d.audioPlaybackErrorMessage(), i.classList.remove("hidden"), i.classList.add("is-warning"), o.classList.remove("hidden");
			}, t.oncanplay = () => {
				a.mayNotPlay || i.classList.remove("is-warning");
			};
		}
		let s = r.audioMetrics || {}, c = s.duration_seconds == null ? "未知" : `${s.duration_seconds}s`;
		n.classList.remove("hidden"), n.innerHTML = `
      <span>时长 ${c}</span>
      <span>音量 ${s.average_volume || 0}</span>
      <span>停顿 ${(s.silence_ratio || 0) * 100}%</span>
      <span>爆音 ${(s.clipping_ratio || 0) * 100}%</span>
    `;
	}
	function y() {
		return r.recordingController ||= u.createRecordingController({
			acquireStream: () => navigator.mediaDevices.getUserMedia({ audio: !0 }),
			createRecorder: (e, t) => t ? new MediaRecorder(e, t) : new MediaRecorder(e),
			createBlob: (e, t) => new Blob(e, t),
			computeMetrics: _,
			publish: ({ blob: e, metrics: t, target: n }) => {
				r.audioBlob = e, r.audioMetrics = t, v(n), o("录音已生成，可以回放或分析");
			},
			onError: (e) => {
				o(e?.name === "NotAllowedError" ? "未获得麦克风权限，请上传音频或使用文字回答" : "录音发生错误，请上传音频或使用文字回答");
			}
		}), r.recordingController;
	}
	async function b(e = "answer") {
		let t = d.audioInputPlan(window, navigator);
		if (!t.canRecord) {
			o("当前浏览器不能直接录音，请上传音频或使用文字回答");
			return;
		}
		let n = await y().start({
			target: e,
			format: t.recorderFormat
		});
		n.ok ? o(e === "room" ? "模拟面试录音开始" : "真实录音开始") : n.reason === "busy" && o("正在启动或录制音频，请先停止当前录音");
	}
	function x() {
		y().stop() || o("当前没有正在录制的音频");
	}
	async function S() {
		y().invalidate();
		let e = mt(a, "audioFileInput").files?.[0];
		e && (r.audioBlob = e, r.audioMetrics = await _(e, "upload"), v("answer"), o("已载入上传音频，可以回放或分析"));
	}
	async function C(e = "answer") {
		if (!r.audioBlob) {
			o("请先录音或上传音频");
			return;
		}
		let c = mt(a, e === "room" ? "roomAnswer" : "answerInput").value.trim();
		if (!c) {
			o("请补充转写文本，AI 需要结合内容和声音一起分析");
			return;
		}
		let l = new FormData(), u = d.audioFileDescriptor(r.audioBlob);
		l.append("audio", r.audioBlob, u.filename), l.append("user_id", String(n)), l.append("transcript", c), Number.isFinite(r.audioMetrics?.duration_seconds) && l.append("duration_seconds", String(r.audioMetrics.duration_seconds)), l.append("metrics", JSON.stringify(r.audioMetrics || {}));
		let f = await s(() => i("/interview/analyze-audio", {
			method: "POST",
			body: l
		}), "AI 正在分析真实录音...");
		if (!f.success) {
			o(f.message || "录音分析失败");
			return;
		}
		let p = {
			score: f.overall_score,
			summary: f.summary,
			voice: f,
			suggestions: f.tips
		};
		if (e === "room") {
			let e = mt(a, "roomFeedback");
			e.classList.remove("hidden"), e.innerHTML = t.renderFeedbackHtml(p);
		} else t.renderFeedback(p);
		await t.loadTrainingRecords();
	}
	function w() {
		let e = d.speechRecognition(window), t = d.audioInputPlan(window, navigator);
		d.applyCapabilityUI(document, {
			speech: e,
			audio: t
		});
	}
	function T() {
		let e = d.speechRecognition(window);
		e.Recognition && (r.recognition = new e.Recognition(), r.recognition.lang = "zh-CN", r.recognition.continuous = !0, r.recognition.interimResults = !0, r.speechController = u.bindSpeechRecognition(r.recognition, {
			getText: () => mt(a, "answerInput").value.replace(/\s*$/, ""),
			setText: (e) => {
				mt(a, "answerInput").value = e;
			},
			setActive: (e) => {
				r.recognizing = e, mt(a, "voiceBtn").classList.toggle("recording", e);
			},
			onError: (e) => {
				let t = e?.error === "not-allowed" || e?.error === "service-not-allowed";
				o(t ? "未获得语音识别权限，请直接使用文字回答" : "语音识别暂时不可用，请直接使用文字回答");
			}
		}));
	}
	function ee() {
		if (!r.recognition) {
			o("当前浏览器不支持语音识别，可以使用 Chrome 尝试");
			return;
		}
		if (r.recognizing) {
			try {
				r.recognition.stop();
			} catch {
				r.speechController?.finish();
			}
			return;
		}
		if (r.speechController?.begin(), !d.startSpeechSafely(r.recognition).ok) {
			r.speechController?.finish(), o("无法启动语音识别，请直接使用文字回答");
			return;
		}
		o("正在语音录入");
	}
	return {
		extensionFromMime: p,
		downloadSaved: g,
		getRecordingController: y,
		startRecording: b,
		stopRecording: x,
		handleUpload: S,
		computeMetrics: _,
		renderPreview: v,
		analyzeRecorded: C,
		applyCapabilities: w,
		setupSpeechRecognition: T,
		toggleVoiceInput: ee
	};
}
//#endregion
//#region frontend/src/interview/interview-renderers.ts
function gt(e) {
	return {
		opening: "自我介绍",
		resume_deep_dive: "项目深挖",
		technical: "技术追问",
		professional: "专业追问",
		behavioral: "行为面",
		candidate_questions: "反问环节",
		finished: "面试结束"
	}[e] || e;
}
function _t(e = "") {
	return String(e).replace(/\\/g, "\\\\").replace(/'/g, "\\'").replace(/\n/g, " ");
}
function vt(e) {
	return {
		general: "通用面试",
		career: "跟随求职方向",
		test: "软件测试",
		python: "Python / Flask",
		frontend: "前端基础",
		ai: "AI Agent",
		tech: "计算机 / 软件 / AI",
		ops: "运营 / 新媒体",
		marketing: "市场 / 销售",
		finance: "财务 / 会计",
		education: "教育 / 师范",
		hr: "行政 / 人事"
	}[e] || e;
}
function yt(e) {
	try {
		return JSON.parse(String(e || "{}"));
	} catch {
		return {};
	}
}
function bt(e) {
	return e ? new Date(String(e)).toLocaleString() : "";
}
function xt(e) {
	return yt(e).summary || "";
}
//#endregion
//#region frontend/src/interview/interview-training.ts
function N(e, t) {
	let n = e(t);
	if (!n) throw Error(`Missing interview training control: #${t}`);
	return n;
}
function St(e) {
	let { userId: t, apiBaseUrl: n, state: r, request: i, byId: a, escapeHtml: o, renderText: s, toast: c, withLoading: l, renderIcons: u, selectedCareerProfile: d, loadDashboard: f, confirmAction: p } = e;
	async function m(e = "all") {
		let t = e === "career" ? d() : e;
		r.currentPracticeCategory = e;
		let n = await i(`/questions?category=${encodeURIComponent(t)}`), s = n.success ? n.data : [];
		N(a, "questionList").innerHTML = s.length ? s.map((t, n) => `
        <article class="question-card">
          <b>${n + 1}. ${o(t.question)}</b>
          <small>${vt(t.category)} · 点击“练习”后可输入自己的回答</small>
          <div class="list-actions">
            <button class="ghost small" data-command="interview-select-question" data-question="${_t(t.question)}" data-category="${_t(e === "career" ? "career" : t.category)}">练习</button>
            <button class="ghost small" data-command="interview-show-sample" data-answer="${_t(t.answer)}">参考答案</button>
          </div>
        </article>
      `).join("") : "<article class=\"question-card\"><b>暂无题目</b><small>换一个分类试试</small></article>";
	}
	function h(e, t) {
		N(a, "practiceQuestion").value = e, r.currentPracticeCategory = t, N(a, "practiceAnswer").focus(), c("题目已放入练习区");
	}
	function g(e) {
		let t = N(a, "practiceResult");
		t.classList.remove("hidden"), t.innerHTML = `<h4>参考答案</h4>${s(e)}`;
	}
	function _(e, t, n, r) {
		return `
      <section class="record-column">
        <h4>${o(e)}<span>${n.length}</span></h4>
        ${n.length ? n.map((e) => `
          <article class="record-card">
            ${r(e)}
            <div class="record-actions">
              <button class="ghost small" data-command="training-view" data-record-type="${_t(t)}" data-record-id="${e.id}">查看详情</button>
              <button class="ghost small danger" data-command="training-delete" data-record-type="${_t(t)}" data-record-id="${e.id}">删除</button>
            </div>
          </article>
        `).join("") : "<article class=\"record-card\"><b>暂无记录</b><small>完成训练后会自动出现在这里</small></article>"}
      </section>
    `;
	}
	async function v() {
		let e = a("trainingRecords");
		if (!e) return;
		let n = await i(`/training-records/${t}`);
		if (!n.success) return;
		let r = n.interviews || [], s = n.practices || [], c = n.audios || [];
		e.innerHTML = `
      ${_("模拟面试", "interview", r, (e) => `
        <b>${o(e.job_title || "模拟面试")}</b>
        <small>${bt(e.created_at)} · ${e.score ?? 0} 分</small>
        <p>${o(xt(e.feedback) || "已完成一轮模拟面试。")}</p>
      `)}
      ${_("答题练习", "practice", s, (e) => `
        <b>${o(vt(e.category))} · ${e.score ?? 0} 分</b>
        <small>${bt(e.created_at)}</small>
        <p>${o(e.question || "")}</p>
      `)}
      ${_("语音录音", "audio", c, (e) => `
        <b>语音表达分析 · ${e.score ?? 0} 分</b>
        <small>${bt(e.created_at)}${e.audio_file ? " · 已保存音频" : ""}</small>
        <p>${o((e.transcript || "").slice(0, 90))}</p>
      `)}
    `, u();
	}
	async function y(e, n) {
		let r = await i(`/training-records/${t}`);
		if (!r.success) {
			c("记录读取失败");
			return;
		}
		let o = ((e === "interview" ? r.interviews : e === "practice" ? r.practices : r.audios) || []).find((e) => Number(e.id) === Number(n));
		if (!o) {
			c("记录不存在或已删除");
			return;
		}
		let s = N(a, "recordDetail");
		s.classList.remove("hidden"), s.innerHTML = x(e, o), s.scrollIntoView({
			behavior: "smooth",
			block: "nearest"
		});
	}
	function b(e) {
		let t = yt(e), n = Array.isArray(t) ? t : t.turns || t.conversation || [];
		return n.length ? n.map((e) => {
			let t = e.role || e.speaker || "记录", n = e.content || e.text || e.question || e.answer || "";
			return `<div class="conversation-line"><b>${o(t)}</b><span>${o(n)}</span></div>`;
		}).join("") : "<div>暂无完整对话记录。</div>";
	}
	function x(e, t) {
		let r = yt(t.feedback), i = yt(t.metrics);
		return e === "audio" ? `
        <h4>语音复盘详情：${t.score ?? 0} 分</h4>
        <div><b>时间</b><br>${bt(t.created_at)}</div>
        <div><b>转写文本</b><br>${o(t.transcript || "暂无转写文本")}</div>
        <div><b>声音指标</b><br>时长 ${i.duration_seconds || 0}s，平均音量 ${i.average_volume || 0}，停顿占比 ${Math.round((i.silence_ratio || 0) * 100)}%，爆音占比 ${Math.round((i.clipping_ratio || 0) * 100)}%</div>
        ${t.audio_file ? `
          <audio controls src="${n}/uploads/${encodeURIComponent(t.audio_file)}"></audio>
          <div class="audio-downloads">
            <button class="ghost small" data-command="training-audio-download" data-audio-file="${_t(t.audio_file)}" data-audio-format="wav">下载 WAV</button>
            <button class="ghost small" data-command="training-audio-download" data-audio-file="${_t(t.audio_file)}" data-audio-format="mp3">下载 MP3</button>
            <button class="ghost small" data-command="training-audio-download" data-audio-file="${_t(t.audio_file)}" data-audio-format="original">下载原始音频</button>
          </div>
          <small>WAV 可由浏览器本地转换；MP3 由后端 ffmpeg 转码生成。</small>
        ` : ""}
        <div><b>AI 建议</b><br>${o(r.summary || "")}</div>
        ${(r.tips || []).map((e) => `<div>• ${o(e)}</div>`).join("")}
      ` : e === "practice" ? `
        <h4>答题记录详情：${t.score ?? 0} 分</h4>
        <div><b>时间</b><br>${bt(t.created_at)}</div>
        <div><b>题目</b><br>${o(t.question || "")}</div>
        <div><b>我的回答</b><br>${o(t.answer || "")}</div>
        <div><b>维度评分</b><br>${Object.entries(r.dimension_scores || {}).map(([e, t]) => `${o(e)}：${o(String(t))}`).join("　") || "暂无"}</div>
        ${(r.problems || []).map((e) => `<div>• ${o(e)}</div>`).join("")}
        ${r.sample_answer ? `<h4>参考答案</h4>${s(r.sample_answer)}` : ""}
        ${r.upgrade ? `<h4>表达升级</h4><div>${o(r.upgrade)}</div>` : ""}
      ` : `
      <h4>模拟面试详情：${t.score ?? 0} 分</h4>
      <div><b>岗位</b><br>${o(t.job_title || "模拟面试")}</div>
      <div><b>时间</b><br>${bt(t.created_at)}</div>
      <div><b>总体反馈</b><br>${o(r.summary || xt(t.feedback) || "暂无总结")}</div>
      ${(r.suggestions || []).map((e) => `<div>• ${o(e)}</div>`).join("")}
      <h4>面试对话</h4>
      ${b(t.conversation)}
    `;
	}
	async function S(e, t) {
		if (!p("确定删除这条训练记录吗？")) return;
		let n = await i(`/training-records/${e}/${t}`, { method: "DELETE" });
		if (!n.success) {
			c(n.message || "删除失败");
			return;
		}
		c("训练记录已删除"), await Promise.all([v(), f()]);
	}
	async function C() {
		if (!p("确定清空所有面试、答题和语音记录吗？")) return;
		let e = await i(`/training-records/${t}/clear`, { method: "DELETE" });
		if (!e.success) {
			c(e.message || "清空失败");
			return;
		}
		c("训练记录已清空"), await Promise.all([v(), f()]);
	}
	async function w() {
		let e = await l(() => i("/interview/professional-pack", {
			method: "POST",
			body: {
				category: N(a, "professionalCategory").value,
				career_profile: d(),
				level: N(a, "professionalLevel").value,
				job_title: N(a, "professionalJobTitle").value || N(a, "interviewJobTitle").value || "目标岗位"
			}
		}), "AI 正在生成专业面试题组...");
		if (!e.success) {
			c(e.message || "题组生成失败");
			return;
		}
		N(a, "professionalPack").innerHTML = e.questions.map((e, t) => `
      <article class="question-card">
        <b>${t + 1}. ${o(e.question)}</b>
        <small>${o(e.focus)} · ${o(e.difficulty)}</small>
        <div class="list-actions">
          <button class="ghost small" data-command="interview-select-professional" data-question="${_t(e.question)}">作答</button>
          <button class="ghost small" data-command="interview-show-professional-reference" data-reference="${_t(e.reference)}">参考思路</button>
        </div>
      </article>
    `).join("");
	}
	function T(e) {
		N(a, "professionalQuestion").value = e, N(a, "professionalAnswer").focus(), c("专业问题已放入作答区");
	}
	function ee(e) {
		let t = N(a, "professionalResult");
		t.classList.remove("hidden"), t.innerHTML = `<h4>参考思路</h4>${s(e)}`;
	}
	async function te() {
		let e = N(a, "professionalQuestion").value.trim(), n = N(a, "professionalAnswer").value.trim();
		if (!e || !n) {
			c("请先选择专业问题并填写回答");
			return;
		}
		let r = await i("/interview/practice-feedback", {
			method: "POST",
			body: {
				question: e,
				answer: n,
				user_id: t,
				category: N(a, "professionalCategory").value,
				career_profile: d(),
				job_title: N(a, "professionalJobTitle").value || N(a, "interviewJobTitle").value || "目标岗位"
			}
		});
		if (!r.success) {
			c(r.message || "评分失败");
			return;
		}
		let l = N(a, "professionalResult");
		l.classList.remove("hidden"), l.innerHTML = `
      <h4>专业回答评分：${r.score} 分</h4>
      <div><b>维度分</b><br>${Object.entries(r.dimension_scores).map(([e, t]) => `${e}：${t}`).join("　")}</div>
      <div><b>命中关键词</b><br>${o((r.hits || []).join("、") || "暂无")}</div>
      ${(r.problems || []).map((e) => `<div>• ${o(e)}</div>`).join("")}
      <h4>参考答案</h4>${s(r.sample_answer)}
      <h4>追问建议</h4>${o(r.follow_up || "把回答继续落到你的项目经历、测试工具和实际结果上。")}
    `, await v();
	}
	async function E() {
		let e = N(a, "practiceQuestion").value.trim(), n = N(a, "practiceAnswer").value.trim();
		if (!e || !n) {
			c("请先填写题目和你的回答");
			return;
		}
		let l = await i("/interview/practice-feedback", {
			method: "POST",
			body: {
				question: e,
				answer: n,
				category: r.currentPracticeCategory,
				career_profile: d(),
				job_title: N(a, "interviewJobTitle").value || "目标岗位",
				user_id: t
			}
		});
		if (!l.success) {
			c(l.message || "评分失败");
			return;
		}
		let u = N(a, "practiceResult");
		u.classList.remove("hidden"), u.innerHTML = `
      <h4>练习评分：${l.score} 分</h4>
      <div><b>维度分</b><br>${Object.entries(l.dimension_scores).map(([e, t]) => `${e}：${t}`).join("　")}</div>
      <div><b>命中关键词</b><br>${o((l.hits || []).join("、") || "暂无")}</div>
      ${(l.problems || []).map((e) => `<div>• ${o(e)}</div>`).join("")}
      <h4>参考答案</h4>${s(l.sample_answer)}
      <h4>表达升级</h4>${o(l.upgrade)}
    `, await v();
	}
	return {
		loadQuestions: m,
		selectQuestion: h,
		showSampleAnswer: g,
		loadRecords: v,
		renderRecordColumn: _,
		viewRecord: y,
		renderRecordDetail: x,
		renderConversation: b,
		deleteRecord: S,
		clearRecords: C,
		loadProfessionalPack: w,
		selectProfessionalQuestion: T,
		showProfessionalReference: ee,
		scoreProfessionalAnswer: te,
		scorePractice: E
	};
}
//#endregion
//#region frontend/src/interview/interview-controller.ts
function P(e, t) {
	let n = e(t);
	if (!n) throw Error(`Missing interview control: #${t}`);
	return n;
}
function Ct(e) {
	let { userId: t, state: n, request: r, byId: i, toast: a, renderIcons: o, selectedCareerProfile: s, buildInterviewStartPayload: c, escapeHtml: l, loadDashboard: u, submission: d } = e;
	function f(e) {
		n.interviewStageIndex = Math.max(0, Number(e.progress || 1) - 1), n.currentInterviewSession = e, P(i, "currentQuestion").textContent = e.question, P(i, "interviewStageLabel").textContent = gt(e.stage);
		let t = Math.min(100, e.progress / e.total * 100), r = P(i, "interviewProgress");
		r.style.width = `${t}%`, r.parentElement?.classList.toggle("has-progress", t > 0), P(i, "roomQuestion").textContent = e.question, P(i, "roomStageLabel").textContent = gt(e.stage), P(i, "roomProgress").style.width = `${t}%`;
	}
	function p(e) {
		f(e), P(i, "roomAnswer").value = "", P(i, "roomFeedback").classList.add("hidden"), P(i, "interviewRoom").classList.remove("hidden"), o();
	}
	async function m() {
		let e = n.interviewOpportunityHandoff, o = e?.resumeId || P(i, "interviewResumeSelect").value || n.resumes[0]?.id;
		if (!o) {
			a("请先保存或选择简历");
			return;
		}
		let l = c({
			user_id: t,
			resume_id: Number(o),
			job_title: P(i, "interviewJobTitle").value || "软件测试工程师",
			jd: P(i, "interviewJd").value,
			career_profile: s(),
			mode: "campus"
		}, e), u = await r("/interview/sessions", {
			method: "POST",
			body: l
		});
		if (!u.success) {
			a(u.message || "面试创建失败");
			return;
		}
		n.activeInterview = u.session_id, n.pendingInterviewSubmission = null, n.interviewSubmitting = !1, n.interviewOpportunityHandoff = null, f(u), P(i, "interviewFeedback").classList.add("hidden"), p(u);
	}
	function h(e) {
		let t = e.voice.dimension_scores || {};
		return `
      <h4>即时反馈：${e.score} 分</h4>
      <div>${l(e.summary)}</div>
      <div>语速：${e.voice.estimated_speech_rate} 字/分钟（${e.voice.pace_label || "自然"}），口头禅：${e.voice.filler_count} 次，结构分：${e.voice.structure_score}</div>
      <div><b>维度分</b><br>${Object.entries(t).map(([e, t]) => `${e}：${t}`).join("　")}</div>
      ${e.voice.audio_quality ? `<div><b>真实录音质量</b><br>${l(e.voice.audio_quality)}</div>` : ""}
      ${e.answer_upgrade ? `<div><b>表达升级</b><br>${l(e.answer_upgrade)}</div>` : ""}
      ${(e.suggestions || []).map((e) => `<div>• ${l(e)}</div>`).join("")}
    `;
	}
	function g(e) {
		let t = P(i, "interviewFeedback");
		t.classList.remove("hidden"), t.innerHTML = h(e);
	}
	async function _() {
		if (!n.activeInterview) {
			a("请先开始模拟面试");
			return;
		}
		if (n.interviewSubmitting) return;
		let e = P(i, "answerInput"), t = e.value.trim();
		if (!t) {
			a("请先输入回答");
			return;
		}
		let o = await d.submitInterviewAnswer(n, t, {
			createId: () => globalThis.crypto && typeof globalThis.crypto.randomUUID == "function" ? globalThis.crypto.randomUUID() : `interview-${Date.now()}-${Math.random().toString(36).slice(2)}`,
			send: (e) => r(`/interview/sessions/${n.activeInterview}/answer`, {
				method: "POST",
				body: {
					answer: e.answer,
					submission_id: e.submissionId,
					expected_stage_index: e.expectedStageIndex
				}
			}),
			reload: () => r(`/interview/sessions/${n.activeInterview}`)
		});
		if (o.kind === "success") {
			let t = o.session;
			f(t), e.value = "", g(t.feedback), t.stage === "finished" && await Promise.all([u(), b.loadRecords()]);
			return;
		}
		if (o.kind === "conflict_recovered") {
			f(o.session), e.value = "", a("面试进度已同步，请回答当前问题");
			return;
		}
		o.kind !== "busy" && a("提交结果不确定，请重试");
	}
	async function v() {
		let e = P(i, "roomAnswer"), t = e.value.trim();
		if (!t) {
			a("请先输入本轮回答");
			return;
		}
		P(i, "answerInput").value = t, await _(), e.value = "";
		let n = P(i, "roomFeedback");
		n.classList.remove("hidden"), n.innerHTML = P(i, "interviewFeedback").innerHTML;
	}
	async function y() {
		let e = P(i, "answerInput").value.trim();
		if (!e) {
			a("请先输入或语音录入回答");
			return;
		}
		let t = await r("/interview/analyze-voice", {
			method: "POST",
			body: { answer: e }
		});
		g({
			score: t.overall_score,
			summary: "表达分析完成",
			voice: t,
			suggestions: t.tips
		});
	}
	let b = St(e), x = ht(e, {
		renderFeedback: g,
		renderFeedbackHtml: h,
		loadTrainingRecords: b.loadRecords
	});
	return {
		start: m,
		updateQuestion: f,
		openRoom: p,
		stageName: gt,
		sendAnswer: _,
		sendRoomAnswer: v,
		renderFeedback: g,
		renderFeedbackHtml: h,
		analyzeVoice: y,
		extensionFromMime: x.extensionFromMime,
		downloadSavedAudio: x.downloadSaved,
		getRecordingController: x.getRecordingController,
		startAudioRecording: x.startRecording,
		stopAudioRecording: x.stopRecording,
		handleAudioUpload: x.handleUpload,
		computeAudioMetrics: x.computeMetrics,
		renderAudioPreview: x.renderPreview,
		analyzeRecordedAudio: x.analyzeRecorded,
		applyBrowserCapabilities: x.applyCapabilities,
		setupSpeechRecognition: x.setupSpeechRecognition,
		toggleVoiceInput: x.toggleVoiceInput,
		loadQuestions: b.loadQuestions,
		escapeAttr: _t,
		categoryName: vt,
		selectQuestion: b.selectQuestion,
		showSampleAnswer: b.showSampleAnswer,
		loadTrainingRecords: b.loadRecords,
		renderRecordColumn: b.renderRecordColumn,
		viewTrainingRecord: b.viewRecord,
		renderRecordDetail: b.renderRecordDetail,
		safeJson: yt,
		renderConversation: b.renderConversation,
		parseFeedbackSummary: xt,
		formatDate: bt,
		deleteTrainingRecord: b.deleteRecord,
		clearTrainingRecords: b.clearRecords,
		loadProfessionalPack: b.loadProfessionalPack,
		selectProfessionalQuestion: b.selectProfessionalQuestion,
		showProfessionalReference: b.showProfessionalReference,
		scoreProfessionalAnswer: b.scoreProfessionalAnswer,
		scorePractice: b.scorePractice
	};
}
//#endregion
//#region frontend/src/interview/interview-media.mjs
var wt = /* @__PURE__ */ n({
	bindRecorderSession: () => At,
	bindSpeechRecognition: () => Mt,
	computeAudioMetrics: () => Dt,
	createObjectUrlRegistry: () => Pt,
	createRecordingController: () => Nt,
	createSpeechTranscriptSession: () => jt,
	decodeAudioBlob: () => Ot
}), Tt = Object.freeze({
	duration_seconds: null,
	peak: 0,
	average_volume: 0,
	silence_ratio: 0,
	pause_count: 0,
	clipping_ratio: 0
});
function Et(e, t, n) {
	if (e !== "recording" || !Number.isFinite(t) || t <= 0) return null;
	let r = n - t;
	return !Number.isFinite(r) || r < 0 || r > 14400 * 1e3 ? null : Math.max(1, Math.round(r / 1e3));
}
async function Dt(e, t = {}) {
	let { source: n = "upload", startedAt: r = 0, now: i = Date.now(), AudioContext: a = null } = t, o = {
		...Tt,
		duration_seconds: Et(n, r, i)
	};
	if (!a) return o;
	let s = null;
	try {
		let t = await e.arrayBuffer();
		s = new a();
		let n = await s.decodeAudioData(t.slice(0)), r = n.getChannelData(0), i = Math.max(1, Math.floor(r.length / 24e3)), o = 0, c = 0, l = 0, u = 0, d = 0, f = !1;
		for (let e = 0; e < r.length; e += i) {
			let t = Math.abs(r[e]);
			o += t * t, c = Math.max(c, t), t < .018 ? (l += 1, f || (d += 1), f = !0) : f = !1, t > .96 && (u += 1);
		}
		let p = Math.ceil(r.length / i);
		return {
			duration_seconds: Number(Number(n.duration || 0).toFixed(2)),
			peak: Number(c.toFixed(3)),
			average_volume: Number(Math.sqrt(o / Math.max(1, p)).toFixed(3)),
			silence_ratio: Number((l / Math.max(1, p)).toFixed(2)),
			pause_count: d,
			clipping_ratio: Number((u / Math.max(1, p)).toFixed(3))
		};
	} catch {
		return o;
	} finally {
		if (s?.close) try {
			await s.close();
		} catch {}
	}
}
async function Ot(e, t) {
	let n = new t();
	try {
		return await n.decodeAudioData(await e.arrayBuffer());
	} finally {
		n.close && await n.close();
	}
}
function kt(e) {
	e?.getTracks?.().forEach((e) => e.stop());
}
function At(e) {
	let { recorder: t, stream: n, token: r, format: i = null, isCurrent: a, createBlob: o, computeMetrics: s, publish: c, onError: l = () => {} } = e, u = [];
	t.ondataavailable = (e) => {
		e.data?.size > 0 && u.push(e.data);
	}, t.onerror = (e) => {
		kt(n), a(r) && l(e);
	}, t.onstop = async () => {
		kt(n);
		let e = t.mimeType || i?.mimeType || "", l = o(u, { type: e }), d = await s(l);
		a(r) && c({
			blob: l,
			metrics: d,
			mimeType: e,
			token: r
		});
	};
}
function jt(e = "") {
	let t = String(e);
	return { update(e) {
		let n = "", r = "";
		for (let t = 0; t < e.results.length; t += 1) {
			let i = e.results[t], a = i?.[0]?.transcript || "";
			i.isFinal ? n += a : r += a;
		}
		return `${t}${n}${r}`;
	} };
}
function Mt(e, t) {
	let { getText: n, setText: r, setActive: i, onError: a } = t, o = !1, s = null, c = () => {
		o = !1, s = null, i(!1);
	};
	return e.onresult = (e) => {
		o && s && r(s.update(e));
	}, e.onend = c, e.onerror = (e) => {
		c(), a(e);
	}, {
		begin() {
			s = jt(n()), o = !0, i(!0);
		},
		finish: c,
		isActive() {
			return o;
		}
	};
}
function Nt(e) {
	let { acquireStream: t, createRecorder: n, createBlob: r, computeMetrics: i, publish: a, onError: o = () => {}, onRecorderChange: s = () => {}, now: c = () => Date.now() } = e, l = 0, u = null, d = null, f = (e) => {
		d = e, s(e?.recorder || null);
	};
	async function p({ target: e, format: s }) {
		if (u !== null || d) return {
			ok: !1,
			reason: "busy"
		};
		let p = ++l;
		u = p;
		let m = null;
		try {
			if (m = await t(), p !== l) return kt(m), {
				ok: !1,
				reason: "cancelled"
			};
			let u = s?.mimeType ? { mimeType: s.mimeType } : void 0, h = n(m, u), g = c();
			return f({
				recorder: h,
				stream: m,
				token: p,
				target: e
			}), At({
				recorder: h,
				stream: m,
				token: p,
				format: s,
				isCurrent: (e) => e === l,
				createBlob: r,
				computeMetrics: (e) => i(e, "recording", g),
				publish: (t) => {
					d?.token === p && f(null), a({
						...t,
						target: e
					});
				},
				onError: (e) => {
					d?.token === p && f(null), o(e);
				}
			}), h.start(), {
				ok: !0,
				recorder: h,
				token: p
			};
		} catch (e) {
			return kt(m), d?.token === p && f(null), o(e), {
				ok: !1,
				reason: "error",
				error: e
			};
		} finally {
			u === p && (u = null);
		}
	}
	function m() {
		l += 1, u = null;
		let e = d;
		if (e) {
			f(null);
			try {
				e.recorder.state === "recording" && e.recorder.stop();
			} finally {
				kt(e.stream);
			}
		}
	}
	function h() {
		return !d || d.recorder.state !== "recording" ? !1 : (d.recorder.stop(), !0);
	}
	return {
		start: p,
		stop: h,
		invalidate: m,
		activeRecorder() {
			return d?.recorder || null;
		}
	};
}
function Pt({ create: e, revoke: t }) {
	let n = /* @__PURE__ */ new Map(), r = (e) => {
		let r = n.get(e);
		r && (t(r), n.delete(e));
	}, i = () => [...n.keys()].forEach(r);
	return {
		replace(t, r) {
			i();
			let a = e(r);
			return n.set(t, a), a;
		},
		get(e) {
			return n.get(e) || null;
		},
		clear: r,
		clearAll: i
	};
}
//#endregion
//#region frontend/src/interview/interview-submission.ts
var Ft = /* @__PURE__ */ n({
	submitInterviewAnswer: () => Lt,
	synchronizeSession: () => It
});
function It(e, t) {
	e.interviewStageIndex = Math.max(0, Number(t.progress || 1) - 1), e.currentInterviewSession = t;
}
async function Lt(e, t, n) {
	if (e.interviewSubmitting) return { kind: "busy" };
	let r = e.pendingInterviewSubmission;
	(!r || r.answer !== t || r.expectedStageIndex !== e.interviewStageIndex) && (r = {
		answer: t,
		submissionId: n.createId(),
		expectedStageIndex: e.interviewStageIndex
	}, e.pendingInterviewSubmission = r), e.interviewSubmitting = !0;
	try {
		let t = await n.send(r);
		if (t?.success) return It(e, t), e.pendingInterviewSubmission = null, {
			kind: "success",
			session: t
		};
		if (t?.code === "interview_stage_conflict") {
			let r = await n.reload();
			return r?.success ? (It(e, r), e.pendingInterviewSubmission = null, {
				kind: "conflict_recovered",
				session: r
			}) : {
				kind: "conflict_reload_failed",
				response: t,
				current: r
			};
		}
		return {
			kind: "uncertain_failure",
			response: t
		};
	} catch (e) {
		return {
			kind: "uncertain_failure",
			error: e
		};
	} finally {
		e.interviewSubmitting = !1;
	}
}
//#endregion
//#region frontend/src/opportunity/application-board.ts
function Rt(e, t) {
	let n = e(t);
	if (!n) throw Error(`Missing application control: #${t}`);
	return n;
}
function zt(e, t) {
	let { userId: n, state: r, request: i, byId: a, escapeHtml: o, renderText: s, toast: c, withLoading: l, renderIcons: u, renderAgentCommandOpportunities: d, applicationPayloadForJob: f, clearApplicationHandoff: p, jumpToModule: m, confirmAction: h } = e;
	async function g() {
		let e = Rt(a, "appCompany").value.trim(), o = Rt(a, "appJob").value.trim();
		if (!e || !o) {
			c("请填写公司和岗位");
			return;
		}
		let s = {
			user_id: n,
			company: e,
			job_title: o,
			status: Rt(a, "appStatus").value,
			city: Rt(a, "appCity").value,
			notes: Rt(a, "appNotes").value,
			...f(r.pendingApplicationHandoff, o)
		};
		r.editingAppId && (delete s.jd_text, delete s.resume_id), Object.keys(s).forEach((e) => s[e] === void 0 && delete s[e]);
		let l = r.editingAppId, d = await i(l ? `/applications/${l}` : "/applications", {
			method: l ? "PUT" : "POST",
			body: s
		});
		if (!d.success) return;
		let m = l || Number(d.application_id);
		c(l ? "投递记录已更新" : "投递记录已添加"), r.editingAppId = null, p(), Rt(a, "saveAppBtn").innerHTML = "<i data-lucide=\"plus\"></i>添加记录";
		for (let e of [
			"appCompany",
			"appJob",
			"appCity",
			"appNotes"
		]) Rt(a, e).value = "";
		await Promise.all([y(), t.loadDashboard()]), Number.isInteger(m) && m > 0 && await t.openWorkspace(m), u();
	}
	async function _(e) {
		let t = await i(`/applications/detail/${e}`);
		if (!t.success) {
			c(t.message || "投递记录不存在");
			return;
		}
		let n = t.data;
		p(), r.editingAppId = e, Rt(a, "appCompany").value = n.company || "", Rt(a, "appJob").value = n.job_title || "";
		let o = Rt(a, "appStatus");
		[...o.options].some((e) => e.value === n.status) || o.add(new Option(`待确认：${n.status || "未设置"}`, n.status, !0, !0)), o.value = n.status || "已投递", Rt(a, "appCity").value = n.city || "", Rt(a, "appNotes").value = n.notes || "", Rt(a, "saveAppBtn").innerHTML = "<i data-lucide=\"save\"></i>更新记录", m("tracker", "add"), u();
	}
	async function v(e) {
		if (!h("确定删除这条投递记录吗？")) return;
		let n = await i(`/applications/${e}`, { method: "DELETE" });
		if (!n.success) {
			c(n.message || "删除失败");
			return;
		}
		c("投递记录已删除"), r.currentOpportunityId === e && t.closeWorkspace(), await Promise.all([y(), t.loadDashboard()]);
	}
	async function y() {
		let e = await i(`/applications/${n}`), t = Rt(a, "applicationList");
		if (!e.success) {
			t.innerHTML = "<div class=\"workspace-message\" role=\"alert\">投递记录加载失败，请稍后重试。</div>";
			return;
		}
		let s = e.data || [];
		r.applications = s;
		let c = Array.isArray(e.canonical_statuses) ? e.canonical_statuses : [];
		r.applicationStatuses = c;
		let l = Rt(a, "appStatus"), f = l.value;
		if (l.innerHTML = c.map((e) => `<option value="${o(e)}">${o(e)}</option>`).join(""), l.value = c.includes(f) ? f : c.includes("已投递") ? "已投递" : c[0] || "", !s.length) {
			t.innerHTML = "<div class=\"opportunity-empty\"><strong>暂无投递</strong><span>添加第一条记录后，这里会按阶段自动成列。</span><button class=\"primary\" data-route-page=\"tracker\" data-route-module=\"add\"><i data-lucide=\"plus\"></i>新增投递</button></div>", d(), u();
			return;
		}
		let p = new Set(c), m = s.filter((e) => e.needs_status_review || !p.has(e.status)), h = /* @__PURE__ */ new Set([
			0,
			2,
			3
		]), g = c.map((e, t) => ({
			stage: e,
			items: s.filter((t) => t.status === e),
			anchor: h.has(t) || e === "Offer"
		})).filter((e) => e.items.length || e.anchor);
		m.length && g.unshift({
			stage: "待确认",
			items: m,
			warning: !0,
			anchor: !1
		}), t.innerHTML = g.map((e) => `
      <section class="kanban-column${e.warning ? " needs-review" : ""}">
        <h4>${e.warning ? "<i data-lucide=\"triangle-alert\" aria-hidden=\"true\"></i>" : ""}${o(e.stage)}<span>${e.items.length}</span></h4>
        ${e.warning ? "<p class=\"status-warning\"><i data-lucide=\"triangle-alert\" aria-hidden=\"true\"></i>旧状态需要确认，请编辑后选择当前阶段。</p>" : ""}
        ${e.items.length ? e.items.map((e) => `
          <article class="kanban-card">
            <strong>${o(e.company)}</strong>
            <span>${o(e.job_title)}</span>
            <span class="status-text">阶段：${o(e.needs_status_review ? `待确认（原状态：${e.status || "未设置"}）` : e.status)}</span>
            <em>${o(e.city || "城市未填")}</em>
            <p>${o(e.notes || "暂无备注，建议补充投递渠道、面试反馈或待办。")}</p>
            <button class="primary small details-command" data-command="opportunity-open" data-opportunity-id="${e.id}"><i data-lucide="panel-right-open"></i>打开详情</button>
            <div class="kanban-card-actions">
              <button class="ghost small" data-command="opportunity-coach" data-opportunity-id="${e.id}">跟进建议</button>
              ${e.needs_status_review ? "" : `<button class="ghost small" data-command="opportunity-advance" data-opportunity-id="${e.id}">推进</button>`}
              <button class="ghost small" data-command="opportunity-edit" data-opportunity-id="${e.id}">编辑</button>
              <button class="ghost small danger" data-command="opportunity-delete" data-opportunity-id="${e.id}">删除</button>
            </div>
          </article>
        `).join("") : "<div class=\"kanban-empty\"><span>暂无记录</span></div>"}
      </section>
    `).join(""), d(), u();
	}
	async function b(e) {
		let r = await i(`/applications/${e}/advance`, {
			method: "POST",
			body: { user_id: n }
		});
		if (!r.success) {
			c(r.message || "推进失败");
			return;
		}
		c(`已推进到：${r.status}`), await Promise.all([y(), t.loadDashboard()]);
	}
	async function x(e) {
		let t = await l(() => i(`/applications/${e}/coach`, {
			method: "POST",
			body: { user_id: n }
		}), "AI 正在整理投递跟进策略...");
		m("tracker", "board");
		let r = Rt(a, "applicationCoachResult");
		r.classList.remove("hidden"), r.innerHTML = `
      <h4>${o(t.title || "投递跟进建议")}</h4>
      <div><b>下一步：</b>${o(t.next_action || "")}</div>
      <div><b>风险点：</b>${o(t.risk || "")}</div>
      <div><b>可发送话术：</b><br>${o(t.message_template || "")}</div>
      ${t.ai_note ? `<div><b>AI 补充：</b><br>${s(t.ai_note)}</div>` : ""}
    `, r.scrollIntoView({
			behavior: "smooth",
			block: "nearest"
		});
	}
	return {
		save: g,
		edit: _,
		remove: v,
		load: y,
		advance: b,
		coach: x
	};
}
//#endregion
//#region frontend/src/opportunity/opportunity-dashboard.ts
function Bt(e, t) {
	let n = e(t);
	if (!n) throw Error(`Missing dashboard control: #${t}`);
	return n;
}
function Vt(e) {
	let { userId: t, request: n, byId: r, escapeHtml: i, renderIcons: a } = e;
	async function o() {
		let e = await n("/salary/evaluate", {
			method: "POST",
			body: {
				job_type: Bt(r, "salaryJob").value,
				experience: Bt(r, "salaryExp").value,
				city: Bt(r, "salaryCity").value,
				skills_count: Number(Bt(r, "salarySkills").value || 0)
			}
		}), t = Bt(r, "salaryResult");
		t.classList.remove("hidden"), t.innerHTML = `<h4>${e.range.min} - ${e.range.max} / 月</h4><div>参考中位：${e.range.avg} / 月</div><div>${i(e.advice)}</div>`;
	}
	function s(e) {
		r("careerPulse") && (Bt(r, "readinessScore").textContent = String(e.score ?? 0), Bt(r, "readinessLabel").textContent = e.label || "待启动", Bt(r, "readinessSummary").textContent = e.summary || "系统会根据简历、JD 匹配、面试训练和投递进度，给出下一步最该做的动作。", Bt(r, "pulseBlockers").innerHTML = (e.blockers || []).map((e) => `<span>${i(e)}</span>`).join(""), Bt(r, "weeklyPlan").innerHTML = (e.weekly_plan || []).map((e, t) => `
        <button class="plan-step" data-route-page="${i(e.page)}" data-route-module="${i(e.module)}">
          <b>${t + 1}</b>
          <span>${i(e.title)}</span>
          <i data-lucide="arrow-right"></i>
        </button>
      `).join(""), a());
	}
	function c(e) {
		let t = r("nextActions");
		t && (t.innerHTML = e.length ? e.map((e) => `
      <article class="next-action-card">
        <div>
          <b>${i(e.title)}</b>
          <small>${i(e.description)}</small>
        </div>
        <button class="ghost small" data-route-page="${i(e.page)}" data-route-module="${i(e.module)}">${i(e.cta || "去处理")}</button>
      </article>
    `).join("") : "");
	}
	async function l() {
		let e = await n(`/dashboard/${t}`);
		e.success && (Bt(r, "statResumes").textContent = String(e.stats.resumes), Bt(r, "statInterviews").textContent = String(e.stats.interviews), Bt(r, "statMatches").textContent = String(e.stats.matches), Bt(r, "statApps").textContent = String(e.stats.applications), c(e.next_actions || []), s(e.career_pulse || {}));
	}
	return {
		evaluateSalary: o,
		load: l,
		renderCareerPulse: s,
		renderNextActions: c
	};
}
//#endregion
//#region frontend/src/opportunity/opportunity-workspace-renderer.ts
function Ht(e, t) {
	let n = e(t);
	if (!n) throw Error(`Missing opportunity workspace control: #${t}`);
	return n;
}
function Ut(e) {
	let { byId: t, escapeHtml: n, renderIcons: r, syncAgentContext: i, parseFeedbackSummary: a } = e;
	function o(e, t = "未设置") {
		let r = e ? new Date(String(e)).toLocaleString() : t;
		return n(r);
	}
	function s(e) {
		let r = e.opportunity || {}, i = r.needs_status_review ? `待确认（原状态：${r.status || "未设置"}）` : r.status || "未设置";
		Ht(t, "opportunity-overview").innerHTML = `
      ${r.needs_status_review ? "<p class=\"status-warning\"><i data-lucide=\"triangle-alert\"></i>这是旧版状态，请编辑并选择当前标准阶段。</p>" : ""}
      <dl class="opportunity-facts">
        <div><dt>公司</dt><dd>${n(r.company || "未填写")}</dd></div>
        <div><dt>岗位</dt><dd>${n(r.job_title || "未填写")}</dd></div>
        <div><dt>阶段</dt><dd>${n(i)}</dd></div>
        <div><dt>城市</dt><dd>${n(r.city || "未填写")}</dd></div>
        <div><dt>优先级</dt><dd>${n(r.priority == null ? "未设置" : String(r.priority))}</dd></div>
        <div><dt>下一步</dt><dd>${o(r.next_action_at)}</dd></div>
        <div><dt>面试时间</dt><dd>${o(r.interview_at)}</dd></div>
        <div><dt>投递时间</dt><dd>${o(r.applied_at || r.created_at)}</dd></div>
      </dl>
      ${r.notes ? `<div class="workspace-note"><b>备注</b><p>${n(r.notes)}</p></div>` : ""}
      <div class="workspace-primary-action"><button type="button" class="primary" data-command="opportunity-edit" data-opportunity-id="${r.id}"><i data-lucide="pencil"></i>编辑机会</button></div>`;
	}
	function c(e) {
		let r = e.matches || [], i = e.opportunity?.jd_text || "";
		Ht(t, "opportunity-match").innerHTML = `
      <section class="workspace-section"><h4>岗位 JD</h4>
        ${i ? `<div class="workspace-long-text">${n(e.opportunity.jd_text)}</div>` : "<div class=\"opportunity-empty\"><b>尚未保存 JD</b><span>回到 JD 匹配区粘贴岗位描述，再生成匹配结果。</span></div>"}
      </section>
      <section class="workspace-section"><h4>最近匹配</h4>
        ${r.length ? `<div class="workspace-list">${r.map((e) => `
          <div class="workspace-row"><div><b>${n(e.job_title || "目标岗位")}</b><span>${n(e.resume_title || "关联简历")} · ${o(e.created_at)}</span></div><strong>${n(e.match_score == null ? "未评分" : `${e.match_score} 分`)}</strong>
          ${e.analysis ? `<p>${n(e.analysis)}</p>` : ""}
          ${Object.keys(e.details || {}).length ? `<pre>${n(JSON.stringify(e.details, null, 2))}</pre>` : ""}</div>`).join("")}</div>` : "<div class=\"opportunity-empty\"><b>尚无匹配结果</b><span>使用这份 JD 和关联简历完成一次匹配。</span></div>"}
      </section>
      <div class="workspace-primary-action"><button type="button" class="primary" data-command="opportunity-use-jd"><i data-lucide="scan-search"></i>${i ? "用此 JD 重新匹配" : "前往 JD 匹配"}</button></div>`;
	}
	function l(e) {
		let r = e.resume;
		Ht(t, "opportunity-resume").innerHTML = r ? `
      <div class="workspace-version">
        <i data-lucide="file-text"></i><div><b>${n(r.title || "未命名简历")}</b><span>${n(r.version_label || "已关联版本")} · ${o(r.updated_at || r.created_at)}</span><small>${n(r.target_job_title || e.opportunity.job_title || "目标岗位")}</small></div>
      </div>
      <div class="workspace-primary-action"><button type="button" class="primary" data-command="opportunity-open-resume" data-resume-id="${r.id}" data-has-original="${r.has_original ? "true" : "false"}"><i data-lucide="external-link"></i>${r.has_original ? "打开简历原件" : "查看简历版本"}</button></div>` : "\n      <div class=\"opportunity-empty\"><b>尚未关联简历版本</b><span>选择一份与该岗位匹配的简历，再从 JD 区新建机会。</span></div>\n      <div class=\"workspace-primary-action\"><button type=\"button\" class=\"primary\" data-route-page=\"resume\" data-route-module=\"input\"><i data-lucide=\"file-plus-2\"></i>准备简历</button></div>";
	}
	function u(e) {
		let r = e.interviews || [], i = e.actions || [], s = i.find((e) => [
			"interview",
			"interview_plan",
			"mock_interview"
		].includes(e.action_type) && ["pending", "in_progress"].includes(e.status));
		Ht(t, "opportunity-interview").innerHTML = `
      <section class="workspace-section"><h4>面试记录</h4>
        ${r.length ? `<div class="workspace-list">${r.map((e) => `
          <div class="workspace-row"><div><b>${n(e.job_title || "模拟面试")}</b><span>状态：${n(e.status || "未设置")} · 阶段：${n(e.current_stage || "未开始")}</span></div>${e.score == null ? "" : `<strong>${n(`${e.score} 分`)}</strong>`}
            ${e.feedback ? `<p>${n(a(e.feedback) || e.feedback)}</p>` : ""}
            ${e.status === "active" ? `<button type="button" class="ghost" data-command="opportunity-continue-interview" data-session-id="${e.id}"><i data-lucide="play"></i>继续面试</button>` : ""}</div>`).join("")}</div>` : "<div class=\"opportunity-empty\"><b>尚无面试记录</b><span>从当前机会开始模拟面试，系统会保留机会和简历关联。</span></div>"}
      </section>
      <section class="workspace-section"><h4>准备行动</h4>
        ${i.length ? `<div class="workspace-list">${i.map((e) => `<div class="workspace-row"><div><b>${n(e.title)}</b><span>${n(e.status || "pending")} · ${o(e.due_at, "无截止时间")}</span></div>${e.description ? `<p>${n(e.description)}</p>` : ""}</div>`).join("")}</div>` : "<div class=\"opportunity-empty\"><b>暂无准备行动</b><span>先开始一轮模拟面试，再根据反馈补充行动。</span></div>"}
      </section>
      <div class="workspace-primary-action"><button type="button" class="primary" data-command="opportunity-prepare-interview"${s?.id ? ` data-action-id="${s.id}"` : ""}><i data-lucide="messages-square"></i>开始新面试</button></div>`;
	}
	function d(e) {
		let r = e.timeline || [];
		Ht(t, "opportunity-timeline").innerHTML = r.length ? `<ol class="workspace-timeline">${r.map((e) => `
        <li><i data-lucide="circle-dot"></i><div><b>${n(e.event_type || "记录更新")}</b><span>${o(e.occurred_at)} · ${n(e.source || "system")}</span></div></li>`).join("")}</ol>` : `<div class="opportunity-empty"><b>暂无时间线事件</b><span>编辑阶段、添加行动或开始面试后，事件会显示在这里。</span></div>
        <div class="workspace-primary-action"><button type="button" class="primary" data-command="opportunity-refresh" data-opportunity-id="${e.opportunity.id}"><i data-lucide="refresh-cw"></i>刷新时间线</button></div>`;
	}
	function f(e) {
		let n = e.opportunity || {};
		Ht(t, "opportunityWorkspaceError").classList.add("hidden"), Ht(t, "opportunityWorkspaceTitle").textContent = `${n.company || "未命名公司"} / ${n.job_title || "目标岗位"}`, Ht(t, "opportunityWorkspaceSubtitle").textContent = `当前阶段：${n.needs_status_review ? "待确认" : n.status || "未设置"}`, s(e), c(e), l(e), u(e), d(e), i(), r();
	}
	return {
		render: f,
		date: o,
		overview: s,
		match: c,
		resume: l,
		interview: u,
		timeline: d
	};
}
//#endregion
//#region frontend/src/opportunity/opportunity-workspace.ts
function Wt(e, t) {
	let n = e(t);
	if (!n) throw Error(`Missing opportunity workspace control: #${t}`);
	return n;
}
function Gt(e) {
	let { state: t, request: n, byId: r, escapeHtml: i, renderIcons: a, syncAgentContext: o, filterModules: s, renderMatchOpportunityNotice: c, jumpToModule: l, openOriginalResume: u, fillResume: d, buildInterviewHandoff: f, toast: p, openInterviewRoom: m, history: h } = e, g = Ut(e);
	async function _(e, n = {}) {
		n.updateUrl !== !1 && document.activeElement instanceof HTMLElement && (t.opportunityOpener = document.activeElement);
		let r = n.historyMode || (n.updateUrl === !1 ? "none" : "push");
		return h.open(e, { historyMode: r });
	}
	async function v(e, i = {}) {
		let a = Number(e);
		if (!Number.isInteger(a) || a <= 0) return !1;
		let c = ++t.opportunityLoadGeneration, l = () => c === t.opportunityLoadGeneration && t.currentOpportunityId === a && (!i.isCurrent || i.isCurrent());
		t.currentOpportunityId = a;
		let u = document.querySelector("[data-section-filter=\"tracker:board\"]");
		u && s("tracker", "board", u), Wt(r, "opportunityWorkspace").classList.remove("hidden"), Wt(r, "opportunityWorkspaceError").classList.add("hidden"), Wt(r, "opportunityWorkspaceTitle").textContent = "正在加载机会详情", Wt(r, "opportunityWorkspaceSubtitle").textContent = "正在读取本地关联记录...";
		let d;
		try {
			d = await n(`/opportunities/${a}/workspace`);
		} catch {
			return l() ? (y(a, "网络连接失败，请检查连接后重试。"), { status: "retryable" }) : { status: "superseded" };
		}
		return l() ? d.success ? (t.currentOpportunityWorkspace = d, g.render(d), o(), C(Wt(r, "opportunity-tab-overview"), !1), Wt(r, "opportunityWorkspace").scrollIntoView({
			behavior: "smooth",
			block: "start"
		}), { status: "ok" }) : [404, 410].includes(d.http_status) ? { status: "stale" } : d.http_status === 403 ? { status: "forbidden" } : (y(a, "机会详情暂时无法加载，请稍后重试。"), { status: "retryable" }) : { status: "superseded" };
	}
	function y(e, t) {
		Wt(r, "opportunityWorkspaceTitle").textContent = "机会详情暂时不可用", Wt(r, "opportunityWorkspaceSubtitle").textContent = "链接已保留，可直接重试。";
		let n = Wt(r, "opportunityWorkspaceError");
		n.classList.remove("hidden"), n.innerHTML = `${i(t)}<button type="button" class="ghost" data-command="opportunity-retry" data-opportunity-id="${e}"><i data-lucide="refresh-cw"></i>重试</button>`, a();
	}
	function b(e) {
		return Wt(r, "opportunityWorkspaceError").classList.add("hidden"), h.reload(e);
	}
	function x(e = {}) {
		let n = Wt(r, "opportunityWorkspace"), i = t.currentOpportunityId !== null || !n.classList.contains("hidden");
		if (t.opportunityLoadGeneration += 1, t.currentOpportunityId = null, t.currentOpportunityWorkspace = null, o(), n.classList.add("hidden"), Wt(r, "opportunityWorkspaceError").classList.add("hidden"), !i) return;
		let a = e.restoreFocus && t.opportunityOpener?.isConnected ? t.opportunityOpener : e.page === "tracker" ? r("applicationBoardHeading") : r("pageTitle");
		t.opportunityOpener = null, a?.focus({ preventScroll: !0 });
	}
	function S() {
		return h.close({
			historyMode: "push",
			restoreFocus: !0
		});
	}
	function C(e, t = !0) {
		e && (document.querySelectorAll(".opportunity-tabs [role=\"tab\"]").forEach((t) => {
			let n = t === e;
			t.setAttribute("aria-selected", String(n)), t.tabIndex = n ? 0 : -1, r(t.getAttribute("aria-controls") || "")?.classList.toggle("hidden", !n);
		}), t && e.focus());
	}
	function w(e) {
		if (![
			"ArrowRight",
			"ArrowLeft",
			"Home",
			"End"
		].includes(e.key)) return;
		e.preventDefault();
		let t = [...document.querySelectorAll(".opportunity-tabs [role=\"tab\"]")], n = t.indexOf(e.currentTarget), r = n;
		e.key === "ArrowRight" && (r = (n + 1) % t.length), e.key === "ArrowLeft" && (r = (n - 1 + t.length) % t.length), e.key === "Home" && (r = 0), e.key === "End" && (r = t.length - 1), C(t[r]);
	}
	function T() {
		let e = t.currentOpportunityWorkspace?.opportunity;
		e && (t.matchOpportunityId = e.id, c(), Wt(r, "jobTitleInput").value = e.job_title || "", Wt(r, "jdInput").value = e.jd_text || "", e.resume_id && (Wt(r, "tailorResumeSelect").value = String(e.resume_id)), l("resume", "jd"));
	}
	function ee(e, t) {
		return t ? u(e) : (l("resume", "input"), d(e));
	}
	function te(e = null) {
		let n = t.currentOpportunityWorkspace;
		if (n?.opportunity) {
			if (t.interviewOpportunityHandoff = f({
				opportunityId: n.opportunity.id,
				resumeId: n.resume?.id,
				actionId: e,
				jobTitle: n.opportunity.job_title,
				jd: n.opportunity.jd_text
			}), !t.interviewOpportunityHandoff) {
				p("请先为该机会关联简历");
				return;
			}
			Wt(r, "interviewJobTitle").value = n.opportunity.job_title || "", Wt(r, "interviewJd").value = n.opportunity.jd_text || "", n.resume?.id && (Wt(r, "interviewResumeSelect").value = String(n.resume.id)), l("interview", "mock"), p("已关联机会和简历，可开始模拟面试");
		}
	}
	async function E(e) {
		let r = await n(`/interview/sessions/${e}`);
		if (!r.success) {
			p(r.message || "面试记录无法继续");
			return;
		}
		t.activeInterview = String(e), t.pendingInterviewSubmission = null, t.interviewSubmitting = !1, l("interview", "mock"), m(r);
	}
	return {
		open: _,
		load: v,
		showError: y,
		retry: b,
		reset: x,
		close: S,
		selectTab: C,
		handleTabKeydown: w,
		render: g.render,
		date: g.date,
		renderOverview: g.overview,
		renderMatch: g.match,
		useJd: T,
		renderResume: g.resume,
		openResume: ee,
		renderInterview: g.interview,
		prepareInterview: te,
		continueInterview: E,
		renderTimeline: g.timeline
	};
}
//#endregion
//#region frontend/src/opportunity/opportunity-controller.ts
function Kt(e) {
	let t = Vt(e), n = Gt(e), r = zt(e, {
		loadDashboard: t.load,
		openWorkspace: (e) => n.open(e),
		closeWorkspace: n.close
	});
	return {
		saveApplication: r.save,
		editApplication: r.edit,
		deleteApplication: r.remove,
		loadApplications: r.load,
		openWorkspace: n.open,
		loadWorkspace: n.load,
		showWorkspaceError: n.showError,
		retryWorkspace: n.retry,
		resetWorkspace: n.reset,
		closeWorkspace: n.close,
		selectTab: n.selectTab,
		handleTabKeydown: n.handleTabKeydown,
		renderWorkspace: n.render,
		workspaceDate: n.date,
		renderOverview: n.renderOverview,
		renderMatch: n.renderMatch,
		useWorkspaceJd: n.useJd,
		renderResume: n.renderResume,
		openWorkspaceResume: n.openResume,
		renderInterview: n.renderInterview,
		prepareInterview: n.prepareInterview,
		continueInterview: n.continueInterview,
		renderTimeline: n.renderTimeline,
		advanceApplication: r.advance,
		coachApplication: r.coach,
		evaluateSalary: t.evaluateSalary,
		loadDashboard: t.load,
		renderCareerPulse: t.renderCareerPulse,
		renderNextActions: t.renderNextActions
	};
}
//#endregion
//#region frontend/src/opportunity/opportunity-history.mjs
function qt(e) {
	let t = new URL(e.location.href), n = t.searchParams.get("opportunity"), r = n === null ? null : Number(n), i = Number.isSafeInteger(r) && r > 0 && String(r) === n ? r : null;
	return {
		page: t.searchParams.get("page"),
		module: t.searchParams.get("module"),
		opportunityId: i,
		hasOpportunity: n !== null
	};
}
function Jt(e) {
	let t = e.window, n = !1, r = null, i = 0, a = null;
	function o(t) {
		let n = {
			page: t.page || null,
			module: t.module || null,
			opportunityId: t.opportunityId || null,
			hasOpportunity: !!t.hasOpportunity
		};
		return n.page && !n.module && n.opportunityId === null && (n.module = e.defaultModule?.(n.page) || null), n;
	}
	function s(e, n = {}) {
		let r = new URL(t.location.href);
		return r.searchParams.set("page", e), r.searchParams.delete("record"), n.module ? r.searchParams.set("module", n.module) : r.searchParams.delete("module"), n.opportunityId ? r.searchParams.set("opportunity", String(n.opportunityId)) : r.searchParams.delete("opportunity"), r;
	}
	function c() {
		let e = new URL(t.location.href);
		e.searchParams.has("opportunity") && (e.searchParams.delete("opportunity"), t.history.replaceState({}, "", e));
	}
	function l(e, n) {
		new URL(t.location.href).href !== e.href && (n === "push" ? t.history.pushState({}, "", e) : n === "replace" && t.history.replaceState({}, "", e));
	}
	function u(t) {
		let n = o(t), i = r;
		return i && e.onRouteTransition?.(i, n), r = n, n.page && e.showPage(n.page), n.page && n.module && e.showModule?.(n.page, n.module), n;
	}
	async function d(t, n = {}) {
		let r = ++i, a = {
			generation: r,
			isCurrent: () => r === i,
			routeDriven: !0
		}, o = u(t);
		if (o.page === "tracker" && o.opportunityId !== null) {
			let t;
			try {
				t = await e.loadWorkspace(o.opportunityId, a);
			} catch (e) {
				t = a.isCurrent() ? {
					status: "retryable",
					error: e
				} : { status: "superseded" };
			}
			if (!a.isCurrent()) return { status: "superseded" };
			let n = t === !0 ? "ok" : t === !1 ? "stale" : t?.status;
			if (n === "stale" || n === "forbidden") {
				e.closeWorkspace({
					routeDriven: !0,
					page: o.page
				}), c();
				let r = u({
					...o,
					module: null,
					opportunityId: null,
					hasOpportunity: !1
				});
				e.focusRoute?.(r), n === "forbidden" ? e.notifyForbidden?.(t) : e.notifyStale?.(t);
			} else n === "retryable" && e.notifyRetryable?.(t);
			return t;
		}
		return e.closeWorkspace({
			routeDriven: !0,
			page: o.page,
			...n.closeContext || {}
		}), o.hasOpportunity && (c(), u({
			...o,
			module: null,
			opportunityId: null,
			hasOpportunity: !1
		})), { status: "ok" };
	}
	async function f() {
		return a = null, d(qt(t));
	}
	async function p(t, n = {}) {
		let i = Number(t);
		if (!Number.isSafeInteger(i) || i <= 0) return e.closeWorkspace({ routeDriven: !1 }), c(), !1;
		if (a?.id === i && r?.page === "tracker" && r.opportunityId === i) return a.promise;
		let o = n.historyMode || "push";
		l(s("tracker", { opportunityId: i }), o);
		let u = {
			id: i,
			promise: d({
				page: "tracker",
				module: null,
				opportunityId: i,
				hasOpportunity: !0
			})
		};
		a = u;
		try {
			return await u.promise;
		} finally {
			a === u && (a = null);
		}
	}
	async function m(e, t = {}) {
		a = null;
		let n = t.historyMode || "push";
		return l(s(e, t), n), d({
			page: e,
			module: t.module || null,
			opportunityId: t.opportunityId || null,
			hasOpportunity: !!t.opportunityId
		});
	}
	async function h(e) {
		return a = null, d({
			page: "tracker",
			module: null,
			opportunityId: Number(e),
			hasOpportunity: !0
		});
	}
	async function g(e = {}) {
		a = null;
		let t = e.historyMode || "replace", n = s(e.page || "tracker", { module: e.module || "board" });
		return t !== "none" && l(n, t), d({
			page: e.page || "tracker",
			module: e.module || "board",
			opportunityId: null,
			hasOpportunity: !1
		}, { closeContext: {
			routeDriven: !e.restoreFocus,
			restoreFocus: !!e.restoreFocus,
			page: e.page || "tracker"
		} });
	}
	function _() {
		n || (n = !0, t.addEventListener("popstate", () => {
			f().catch((t) => e.notifyRetryable?.({
				status: "retryable",
				error: t
			}));
		}));
	}
	return {
		bind: _,
		close: g,
		navigate: m,
		open: p,
		readRoute: () => qt(t),
		reload: h,
		sync: f
	};
}
//#endregion
//#region frontend/src/opportunity/opportunity-handoffs.ts
var Yt = (e) => Number.isSafeInteger(Number(e)) && Number(e) > 0, Xt = (e) => String(e || "").trim().toLocaleLowerCase();
function Zt(e) {
	return !Yt(e?.opportunityId) || !Yt(e?.resumeId) ? null : Object.freeze({
		opportunityId: Number(e.opportunityId),
		resumeId: Number(e.resumeId),
		actionId: Yt(e.actionId) ? Number(e.actionId) : null,
		jobTitle: String(e.jobTitle || "").trim(),
		jd: String(e.jd || "")
	});
}
function Qt(e, t) {
	if (!t || !Yt(t.opportunityId) || !Yt(t.resumeId)) return { ...e };
	let n = {
		...e,
		application_id: t.opportunityId,
		resume_id: t.resumeId,
		job_title: t.jobTitle,
		jd: t.jd
	};
	return Yt(t.actionId) && (n.action_id = t.actionId), n;
}
function $t(e) {
	return String(e?.jobTitle || "").trim() ? Object.freeze({
		jobTitle: String(e.jobTitle).trim(),
		jd: String(e.jd || ""),
		resumeId: Yt(e.resumeId) ? Number(e.resumeId) : null
	}) : null;
}
function en(e, t) {
	if (!e || Xt(e.jobTitle) !== Xt(t)) return {};
	let n = {};
	return e.jd && (n.jd_text = e.jd), Yt(e.resumeId) && (n.resume_id = e.resumeId), n;
}
function tn(e, t) {
	let n = { ...e };
	return Yt(t) && (n.application_id = Number(t)), n;
}
function nn(e, t, n, r) {
	let i = e?.page === n && e?.module === r, a = t?.page === n && t?.module === r;
	return i && !a;
}
//#endregion
//#region frontend/src/resume/resume-controller.ts
function F(e, t) {
	let n = e(t);
	if (!n) throw Error(`Missing resume control: #${t}`);
	return n;
}
function rn(e) {
	let { userId: t, state: n, request: r, byId: i, escapeHtml: a, toast: o, renderIcons: s, syncAgentContext: c, loadDashboard: l, downloadResponse: u, withLoading: d, jumpToModule: f, closeAgentDrawer: p, apiBaseUrl: m, renderText: h, selectedCareerProfile: g, careerProfileLabel: _, clearMatchOpportunityLink: v, buildMatchPayload: y } = e;
	function b(e = "") {
		F(i, "editingResumeNotice").classList.toggle("hidden", !n.editingResumeId);
		let t = F(i, "editingResumeText");
		t.textContent = e ? `当前版本：${e}。修改后点击“更新当前简历”保存。` : "修改后点击“更新当前简历”保存。";
	}
	function x() {
		let e = `<option value="">选择简历</option>${n.resumes.map((e) => `<option value="${e.id}">${a(e.title)}</option>`).join("")}`;
		for (let t of [
			"tailorResumeSelect",
			"interviewResumeSelect",
			"exportResumeSelect",
			"analysisResumeSelect",
			"skillResumeSelect"
		]) F(i, t).innerHTML = e;
	}
	async function S() {
		let e = await r(`/resumes/${t}`);
		n.resumes = e.success ? e.data : [], F(i, "resumeCount").textContent = String(n.resumes.length), F(i, "resumeList").innerHTML = n.resumes.length ? n.resumes.map((e) => `
        <article class="list-item" data-resume-id="${e.id}" tabindex="-1">
          <b>${a(e.title)}</b>
          <small>${new Date(e.updated_at || e.created_at || "").toLocaleString()}${e.file_type ? ` · 原件 ${a(e.file_type.toUpperCase())}` : ""}</small>
          <div class="list-actions">
            <button class="ghost small" data-command="resume-edit" data-resume-id="${e.id}">编辑</button>
            <button class="ghost small" data-command="resume-open-original" data-resume-id="${e.id}">打开原件</button>
            <label class="ghost small file-action">替换原件<input type="file" accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg" data-command-change="resume-replace-original" data-resume-id="${e.id}"></label>
            <button class="ghost small" data-command="resume-analyze" data-resume-id="${e.id}">诊断</button>
            <button class="ghost small" data-command="resume-delete" data-resume-id="${e.id}">删除</button>
          </div>
        </article>
      `).join("") : "<div class=\"list-item\"><b>暂无简历</b><small>先保存一份简历</small></div>", x(), c(), s();
	}
	async function C(e) {
		let t = await r(`/resumes/detail/${e}`);
		if (!t.success) return;
		F(i, "resumeTitle").value = t.data.title;
		let a = F(i, "resumeContent");
		a.value = t.data.content, n.editingResumeId = e, F(i, "saveResumeBtn").innerHTML = "<i data-lucide=\"save\"></i>更新当前简历", b(t.data.title), s(), f("resume", "input"), F(i, "resumeTitle").focus(), a.scrollTop = 0, o(`正在编辑：${t.data.title}`);
	}
	function w() {
		p(), f("resume", "input");
		let e = F(i, "resumeFile");
		e.focus({ preventScroll: !0 }), e.click();
	}
	function T() {
		let e = F(i, "resumeFile").files?.[0], t = F(i, "resumeTitle");
		!e || t.value.trim() || (t.value = e.name.replace(/\.[^.]+$/, "").slice(0, 300));
	}
	function ee() {
		n.editingResumeId = null, F(i, "resumeTitle").value = "", F(i, "resumeContent").value = "", F(i, "resumeFile").value = "", F(i, "saveResumeBtn").innerHTML = "<i data-lucide=\"save\"></i>保存简历", b(), s(), o("已退出简历编辑模式");
	}
	function te(e) {
		window.open(`${m}/resumes/${e}/original`, "_blank");
	}
	async function E() {
		let e = F(i, "resumeFile"), a = e.files?.[0], c = F(i, "resumeTitle").value.trim(), u = F(i, "resumeContent").value.trim();
		if (!c) {
			o("请填写简历标题");
			return;
		}
		let d;
		if (a) {
			let e = new FormData();
			e.append("file", a), e.append("user_id", String(t)), e.append("title", c), d = await r("/resumes/upload", {
				method: "POST",
				body: e
			});
		} else if (n.editingResumeId) {
			if (!u) {
				o("请粘贴简历内容或上传文件");
				return;
			}
			d = await r(`/resumes/${n.editingResumeId}`, {
				method: "PUT",
				body: {
					title: c,
					content: u
				}
			});
		} else {
			if (!u) {
				o("请粘贴简历内容或上传文件");
				return;
			}
			d = await r("/resumes", {
				method: "POST",
				body: {
					user_id: t,
					title: c,
					content: u
				}
			});
		}
		if (!d.success) {
			o(d.message || "保存失败");
			return;
		}
		o(n.editingResumeId ? "简历已更新" : "简历已保存"), e.value = "", n.editingResumeId = null, F(i, "saveResumeBtn").innerHTML = "<i data-lucide=\"save\"></i>保存简历", b(), await S(), await l(), s();
	}
	function ne() {
		return n.resumes[0]?.id;
	}
	async function re(e) {
		let t = F(i, "exportResumeSelect").value || ne();
		if (!t) {
			o("请先选择要导出的简历");
			return;
		}
		if (!r.raw) throw Error("ApiClient.raw is required for resume exports");
		let n = await r.raw(`/resumes/${t}/export/${e}`);
		await u(n, e === "pdf" ? "resume.pdf" : "resume.docx");
	}
	async function ie(e, t) {
		let n = F(i, t), a = n.files?.[0];
		if (!a) return;
		let o = new FormData();
		if (o.append("file", a), !r.raw) throw Error("ApiClient.raw is required for document conversion");
		let s = await r.raw(`/convert/${e}`, {
			method: "POST",
			body: o
		});
		await u(s, e === "pdf-to-word" ? "converted.docx" : "converted.pdf"), n.value = "";
	}
	async function ae() {
		let e = await r("/resume-generator", {
			method: "POST",
			body: {
				name: "唐乐",
				job_target: "软件测试工程师",
				skills: "Python, Flask, Selenium, Pytest, JMeter, Postman, MySQL"
			}
		});
		F(i, "resumeTitle").value = "唐乐-软件测试工程师-项目版", F(i, "resumeContent").value = e.resume_content, o("已生成一份可继续修改的示例简历");
	}
	function D(e) {
		let t = F(i, "resumeAuditResult");
		t.classList.remove("hidden"), t.innerHTML = `
      <h4>综合评分：${e.score}</h4>
      <div class="score-grid">
        ${Object.entries(e.section_scores || {}).map(([e, t]) => `<div><span>${a(e)}</span><b>${t}</b></div>`).join("")}
      </div>
      <div><b>一句话定位</b><br>${a(e.positioning)}</div>
      <div><b>优势证据</b><br>${(e.strengths || []).map((e) => `• ${a(e)}`).join("<br>")}</div>
      <div><b>客观锐评</b><br>${(e.brutal_comments || []).map((e) => `• ${a(e)}`).join("<br>")}</div>
      <div><b>HR 初筛风险</b><br>${(e.risks || []).map((e) => `• ${a(e)}`).join("<br>")}</div>
      <div><b>证据缺口</b><br>${(e.evidence_gaps || []).map((e) => `• ${a(e)}`).join("<br>")}</div>
      <div><b>优先修改项</b><br>${(e.actions || []).map((e) => `• ${a(e)}`).join("<br>")}</div>
      <div><b>项目经历建议</b><br>${(e.project_suggestions || []).map((e) => `• ${a(e)}`).join("<br>")}</div>
      <div class="result-actions">
        <button class="primary" data-command="resume-improve-selected">生成优化版并保存</button>
        <button class="ghost" data-route-page="resume" data-route-module="jd">去做 JD 优化</button>
        <button class="ghost" data-route-page="resume" data-route-module="skills">看技能图谱</button>
        <button class="ghost" data-route-page="interview" data-route-module="mock">去模拟面试</button>
      </div>
    `;
	}
	async function oe(e) {
		let t = await d(() => r(`/resumes/${e}/audit`, {
			method: "POST",
			body: {
				job_title: F(i, "analysisJobTitle").value || F(i, "jobTitleInput").value,
				jd: F(i, "analysisJdInput").value || F(i, "jdInput").value
			}
		}), "AI 正在诊断简历表达...");
		F(i, "analysisResumeSelect").value = String(e), f("resume", "analysis"), D(t);
	}
	function se() {
		return F(i, "analysisResumeSelect").value || ne();
	}
	async function O() {
		let e = se();
		if (!e) {
			o("请先选择要分析的简历");
			return;
		}
		let t = await d(() => r(`/resumes/${e}/audit`, {
			method: "POST",
			body: {
				job_title: F(i, "analysisJobTitle").value,
				jd: F(i, "analysisJdInput").value,
				career_profile: g()
			}
		}), "AI 正在做简历结构诊断...");
		if (!t.success) {
			o(t.message || "诊断失败");
			return;
		}
		D(t);
	}
	async function k() {
		let e = se();
		if (!e) {
			o("请先选择要修改的简历");
			return;
		}
		let t = await d(() => r(`/resumes/${e}/improve`, {
			method: "POST",
			body: {
				job_title: F(i, "analysisJobTitle").value || F(i, "jobTitleInput").value,
				jd: F(i, "analysisJdInput").value || F(i, "jdInput").value,
				career_profile: g(),
				save: !0
			}
		}), "AI 正在生成可投递优化版...");
		if (!t.success) {
			o(t.message || "优化失败");
			return;
		}
		let n = F(i, "resumeAuditResult");
		n.classList.remove("hidden"), n.innerHTML = `
      <h4>已生成优化版：${a(t.new_title || "新简历版本")}</h4>
      <div><b>${t.ai_used ? "AI 深度改写：已通读完整简历并按目标岗位调整表达。" : "本地事实保真版：模型不可用时保留原始事实并完成结构整理。"}</b></div>
      <div><b>改写策略</b><br>${(t.strategy || []).map((e) => `• ${a(e)}`).join("<br>")}</div>
      <h4>优化内容预览</h4>${h(t.improved_resume || "")}
      <div class="result-actions">
        <button class="primary" data-route-page="resume" data-route-module="manage">查看我的简历</button>
        <button class="ghost" data-route-page="resume" data-route-module="export">导出新版本</button>
        <button class="ghost" data-command="prepare-interview-from-jd">带入模拟面试</button>
      </div>
    `, await S(), await l();
	}
	async function ce(e) {
		await r(`/resumes/${e}`, { method: "DELETE" }), o("简历已删除"), await Promise.all([S(), l()]);
	}
	function le() {
		return F(i, "tailorResumeSelect").value || ne();
	}
	function ue() {
		return F(i, "skillResumeSelect").value || ne();
	}
	async function de() {
		let e = le();
		if (!e) {
			o("请先选择简历");
			return;
		}
		let t = await d(() => r(`/resumes/${e}/tailor`, {
			method: "POST",
			body: {
				job_title: F(i, "jobTitleInput").value,
				jd: F(i, "jdInput").value,
				career_profile: g()
			}
		}), "AI 正在按 JD 优化简历..."), n = F(i, "tailorResult");
		n.classList.remove("hidden");
		let s = t.jd_focus || {};
		n.innerHTML = `
      <h4>匹配分：${t.match_score}</h4>
      <div class="score-grid">
        ${Object.entries(t.score_detail || {}).map(([e, t]) => `<div><span>${a(e)}</span><b>${t}</b></div>`).join("")}
      </div>
      <div><b>候选人定位</b><br>${a(t.positioning)}</div>
      <div><b>客观锐评</b><br>${(t.brutal_comments || []).map((e) => `• ${a(e)}`).join("<br>")}</div>
      <div><b>JD 聚焦</b><br>
        硬技能：${a((s.硬技能 || []).join("、") || "未明显出现")}<br>
        测试能力：${a((s.测试能力 || []).join("、") || "未明显出现")}<br>
        AI 能力：${a((s["AI 能力"] || []).join("、") || "未明显出现")}
      </div>
      <div><b>已命中</b><br>${a((t.matched_keywords || []).join("、") || "暂无")}</div>
      <div><b>待补齐</b><br>${a((t.keyword_gaps || []).join("、") || "暂无")}</div>
      <div><b>面试讲述要点</b><br>${(t.interview_talking_points || []).map((e) => `• ${a(e)}`).join("<br>")}</div>
      <h4>优化版本</h4>${h(t.ai_rewrite || t.tailored_resume)}
      <div class="result-actions">
        <button class="primary" data-command="prepare-interview-from-jd">带入模拟面试</button>
        <button class="ghost" data-command="prepare-application-from-jd">新增投递记录</button>
        <button class="ghost" data-route-page="resume" data-route-module="export">去导出简历</button>
      </div>
    `;
	}
	async function A() {
		let e = le();
		if (!e) {
			o("请先选择简历");
			return;
		}
		let t = y({
			resume_id: Number(e),
			job_title: F(i, "jobTitleInput").value,
			jd: F(i, "jdInput").value,
			job_requirements: F(i, "jdInput").value,
			career_profile: g()
		}, n.matchOpportunityId), s = await d(() => r("/job-match", {
			method: "POST",
			body: t
		}), "AI 正在计算岗位匹配度...");
		if (!s.success) {
			o(s.message || "岗位匹配失败");
			return;
		}
		v();
		let c = F(i, "tailorResult");
		c.classList.remove("hidden"), c.innerHTML = `<h4>岗位匹配：${s.match_score}</h4>${h(s.analysis)}<br><b>待补齐：</b>${a((s.missing_keywords || []).join("、"))}
      <div class="result-actions">
        <button class="primary" data-command="prepare-interview-from-jd">带入模拟面试</button>
        <button class="ghost" data-command="prepare-application-from-jd">新增投递记录</button>
      </div>`, await l();
	}
	async function j() {
		let e = F(i, "jdInput").value.trim();
		if (!e) {
			o("请先粘贴岗位 JD");
			return;
		}
		let t = await d(() => r("/ai/analyze-jd", {
			method: "POST",
			body: {
				jd_content: e,
				job_title: F(i, "jobTitleInput").value,
				career_profile: g()
			}
		}), "AI 正在拆解 JD..."), n = F(i, "tailorResult");
		n.classList.remove("hidden");
		let s = t.focus || {};
		n.innerHTML = `
      <h4>JD 岗位画像</h4>
      <div><b>求职方向</b><br>${a(t.profile?.label || _())}</div>
      <div><b>核心关键词</b><br>${a((t.keywords || []).join("、") || "暂无")}</div>
      <div><b>能力聚焦</b><br>
        ${Object.entries(s).map(([e, t]) => `${a(e)}：${a((t || []).join("、") || "未明显出现")}`).join("<br>")}
      </div>
      <div><b>风险提示</b><br>${(t.risk_flags || []).map((e) => `• ${a(e)}`).join("<br>") || "暂无明显风险词"}</div>
      ${h(t.content || "")}
      <div class="result-actions">
        <button class="primary" data-command="resume-tailor">用这份 JD 优化简历</button>
        <button class="ghost" data-command="prepare-interview-from-jd">带入模拟面试</button>
      </div>
    `;
	}
	async function fe() {
		let e = ue();
		if (!e) {
			o("请先选择简历");
			return;
		}
		let t = await r("/skills/radar", {
			method: "POST",
			body: {
				resume_id: Number(e),
				career_profile: g(),
				job_title: F(i, "analysisJobTitle").value || F(i, "jobTitleInput").value
			}
		}), s = window.Chart;
		n.skillChart && n.skillChart.destroy(), n.skillChart = typeof s == "function" ? new s(F(i, "skillChart"), {
			type: "radar",
			data: {
				labels: t.radar_data.map((e) => e.category),
				datasets: [{
					label: "能力值",
					data: t.radar_data.map((e) => e.score),
					backgroundColor: "rgba(255,122,182,0.18)",
					borderColor: "#ff7ab6",
					pointBackgroundColor: "#66dbc2"
				}]
			},
			options: {
				scales: { r: {
					min: 0,
					max: 10
				} },
				plugins: { legend: { display: !1 } }
			}
		}) : null;
		let c = F(i, "skillResult");
		c.classList.remove("hidden"), c.innerHTML = `
      <h4>技能图谱解读</h4>
      ${(t.radar_data || []).map((e) => `
        <div><b>${a(e.category)}：${e.score}/10</b><br>
        已命中：${a((e.matched || []).join("、") || "暂无")}<br>
        建议：${a(e.suggestion || "补充真实项目证据，把技能写进项目过程和结果。")}</div>
      `).join("")}
      <div class="result-actions">
        <button class="primary" data-route-page="resume" data-route-module="analysis">去修改简历</button>
        <button class="ghost" data-route-page="interview" data-route-module="professional">按短板练专业面试</button>
      </div>
    `;
	}
	async function pe(e, t) {
		let a = t.files?.[0];
		if (!a) return;
		let s = new FormData();
		s.append("file", a);
		let c = await d(() => r(`/resumes/${e}/replace-file`, {
			method: "POST",
			body: s
		}), "正在替换并解析原始简历...");
		if (t.value = "", !c.success) {
			o(c.message || "替换失败");
			return;
		}
		if (o("原文件已替换，文本内容已重新解析"), await S(), n.editingResumeId === e) {
			let t = await r(`/resumes/detail/${e}`);
			F(i, "resumeContent").value = t.data.content || "";
		}
	}
	return {
		load: S,
		updateSelects: x,
		fill: C,
		openUploadFromAgent: w,
		fillTitleFromFile: T,
		setEditNotice: b,
		cancelEdit: ee,
		openOriginal: te,
		save: E,
		export: re,
		convertDocument: ie,
		generate: ae,
		renderAudit: D,
		analyze: oe,
		selectedAnalysisId: se,
		auditSelected: O,
		improveSelected: k,
		remove: ce,
		selectedResumeId: ne,
		selectedTailorId: le,
		selectedSkillId: ue,
		tailor: de,
		match: A,
		analyzeJd: j,
		renderSkills: fe,
		replaceOriginal: pe
	};
}
//#endregion
//#region frontend/src/shared/api-client.ts
function an(e = {}) {
	let t = e.location || { protocol: "" }, n = String(e.runtimeConfig?.apiBaseUrl || "").replace(/\/+$/, "");
	return n ? n.endsWith("/api") ? n : `${n}/api` : t.protocol === "file:" ? "http://localhost:5000/api" : "/api";
}
function on(e) {
	return Array.isArray(e) ? !0 : !e || typeof e != "object" ? !1 : Object.getPrototypeOf(e) === Object.prototype;
}
function sn(e = {}) {
	let t = String(e.baseUrl || "").replace(/\/+$/, ""), n = e.fetch || globalThis.fetch?.bind(globalThis);
	if (!n) throw Error("fetch implementation is required");
	function r(e) {
		return `${t}/${String(e || "").replace(/^\/+/, "")}`;
	}
	function i(e = {}) {
		let t = {
			method: "GET",
			...e
		};
		return on(t.body) && (t.headers = {
			"Content-Type": "application/json",
			...t.headers || {}
		}, t.body = JSON.stringify(t.body)), t;
	}
	async function a(e, t = {}) {
		return n(r(e), i(t));
	}
	return Object.assign(async (e, t = {}) => {
		let n;
		try {
			n = await a(e, t);
		} catch {
			return {
				success: !1,
				message: "网络请求失败，请检查连接后重试。",
				error_code: "network_error"
			};
		}
		if (n.status === 204) return { success: !0 };
		if ((n.headers.get("content-type") || "").includes("application/json")) {
			let e;
			try {
				e = await n.json();
			} catch {
				return {
					success: !1,
					message: "服务器返回了无法解析的数据。",
					error_code: "invalid_response",
					http_status: n.status
				};
			}
			if (n.ok || !e || typeof e != "object") return e;
			let t = e.detail, r = typeof t == "string" ? t : Array.isArray(t) && t[0]?.msg ? t[0].msg : "";
			return {
				success: !1,
				...e,
				message: e.message || r || "请求处理失败。",
				http_status: n.status
			};
		}
		let r = await n.text(), i = {
			success: n.ok,
			content: r,
			...n.ok ? {} : { message: r || "请求处理失败。" }
		};
		return n.ok ? i : {
			...i,
			http_status: n.status
		};
	}, { raw: a });
}
//#endregion
//#region frontend/src/shared/runtime-ui.ts
function cn(e, t = window, n = document) {
	let r;
	function i(e) {
		return n.getElementById(e);
	}
	function a() {
		let e = t.lucide;
		if (!e || typeof e.createIcons != "function") return !1;
		try {
			return e.createIcons(), !0;
		} catch (e) {
			return console.warn("Icon rendering is unavailable; text controls remain usable.", e), !1;
		}
	}
	async function o(e, t = "AI 正在整理你的求职策略...") {
		let n = i("loadingLayer"), r = n?.querySelector("span");
		r && (r.textContent = t), n?.classList.remove("hidden");
		try {
			return await e();
		} finally {
			n?.classList.add("hidden");
		}
	}
	function s(n = "tap") {
		if (!e.soundEnabled) return;
		let r = t.AudioContext || t.webkitAudioContext;
		if (r) try {
			let t = e.audioContext || new r();
			e.audioContext = t, t.state === "suspended" && t.resume();
			let i = t.currentTime, a = t.createOscillator(), o = t.createGain(), s = {
				tap: {
					freq: 520,
					duration: .055,
					volume: .018
				},
				jump: {
					freq: 660,
					duration: .075,
					volume: .022
				},
				success: {
					freq: 840,
					duration: .09,
					volume: .025
				},
				warn: {
					freq: 260,
					duration: .08,
					volume: .018
				}
			}, c = s[n] || s.tap;
			a.type = "sine", a.frequency.setValueAtTime(c.freq, i), a.frequency.exponentialRampToValueAtTime(Math.max(120, c.freq * .82), i + c.duration), o.gain.setValueAtTime(1e-4, i), o.gain.exponentialRampToValueAtTime(c.volume, i + .01), o.gain.exponentialRampToValueAtTime(1e-4, i + c.duration), a.connect(o), o.connect(t.destination), a.start(i), a.stop(i + c.duration + .02);
		} catch (e) {
			console.warn("UI sound skipped", e);
		}
	}
	function c(e, t = {}) {
		let n = i("toast");
		n && (n.textContent = e, n.classList.remove("hidden"), r && clearTimeout(r), r = setTimeout(() => n.classList.add("hidden"), 2600), t.silent || s(/失败|请先|不支持|不存在|错误/.test(e) ? "warn" : "success"));
	}
	function l(e = "") {
		let t = n.createElement("div");
		return t.textContent = String(e), t.innerHTML;
	}
	function u(e = "") {
		return l(e).replace(/^### (.*)$/gm, "<h5>$1</h5>").replace(/^## (.*)$/gm, "<h4>$1</h4>").replace(/^\s*---+\s*$/gm, "<hr>").replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/^(\d+)\. (.*)$/gm, "<div>$1. $2</div>").replace(/^- (.*)$/gm, "<div>• $1</div>").replace(/\n/g, "<br>");
	}
	function d(e, t) {
		let r = URL.createObjectURL(e), i = n.createElement("a");
		i.href = r, i.download = t, n.body.appendChild(i), i.click(), i.remove(), URL.revokeObjectURL(r);
	}
	async function f(e, t) {
		if (!e.ok) {
			let t = await e.text();
			try {
				c(JSON.parse(t).message || "文件处理失败");
			} catch {
				c("文件处理失败");
			}
			return;
		}
		let n = (e.headers.get("content-disposition") || "").match(/filename\*=UTF-8''([^;]+)|filename="?([^"]+)"?/i), r = decodeURIComponent(n?.[1] || n?.[2] || t);
		d(await e.blob(), r), c("文件已生成并开始下载");
	}
	return {
		byId: i,
		renderIcons: a,
		withLoading: o,
		playTone: s,
		toast: c,
		escapeHtml: l,
		renderText: u,
		downloadBlob: d,
		downloadResponse: f
	};
}
//#endregion
//#region frontend/src/shell/shell-controller.ts
var ln = {
	home: "项目总览",
	resume: "简历实验室",
	interview: "面试训练场",
	tracker: "投递看板",
	agent: "求职指挥台"
};
function un(e) {
	let { state: t, byId: n, history: r, playTone: i, syncAgentContext: a, loadAgentCommandCenter: o, routeLeavesFlow: s, clearApplicationHandoff: c, clearMatchOpportunityLink: l, pageTitles: u = ln, windowObject: d = window, documentObject: f = document } = e, p = !1;
	function m() {
		p || (p = !0, f.addEventListener("click", (e) => {
			let t = e.target;
			if (!(t instanceof Element)) return;
			let n = t.closest("[data-page]")?.dataset.page;
			n && (i("jump"), b(n));
		}));
	}
	function g(e) {
		let r = n(`page-${e}`);
		if (!r) return;
		t.currentPage !== e && (t.currentModule = ""), t.currentPage = e, f.querySelectorAll(".page").forEach((e) => e.classList.remove("active")), r.classList.add("active"), f.querySelectorAll(".nav-item").forEach((t) => {
			t.classList.toggle("active", t.dataset.page === e);
		});
		let i = n("pageTitle");
		i && (i.textContent = u[e] || "JobHunter AI"), a(), e === "agent" && o(), h(d, e), d.scrollTo({
			top: 0,
			behavior: "smooth"
		});
	}
	async function _() {
		await r().sync(), new URLSearchParams(d.location.search).get("record") === "audio" && d.setTimeout(() => {
			[...f.querySelectorAll(".record-card")].find((e) => e.textContent?.includes("语音") || e.textContent?.includes("录音") || e.textContent?.includes("表达"))?.querySelector(".record-actions button")?.click();
		}, 500);
	}
	function v(e, t, n) {
		f.querySelectorAll(`[data-filter-page="${e}"] button`).forEach((e) => {
			e.classList.toggle("active", e === n);
		}), f.querySelectorAll(`.module-panel[data-module-page="${e}"]`).forEach((e) => {
			e.classList.toggle("is-filtered-out", e.dataset.module !== t);
		});
	}
	function y(e, n) {
		e === t.currentPage && (t.currentModule = n || "");
		let r = f.querySelector(`[data-section-filter="${e}:${n}"]`);
		r && v(e, n, r), a();
	}
	function b(e, t = null, n = {}) {
		return r().navigate(e, {
			module: t,
			historyMode: n.historyMode || "push"
		});
	}
	function x(e, t) {
		return b(e, t);
	}
	function S(e) {
		return (f.querySelector(`[data-filter-page="${e}"] [data-section-filter]`)?.dataset.sectionFilter)?.split(":")[1] || null;
	}
	function C(e, n) {
		t.pendingApplicationHandoff && s(e, n, "tracker", "add") && c(), t.matchOpportunityId && s(e, n, "resume", "jd") && l(), t.interviewOpportunityHandoff && s(e, n, "interview", "mock") && (t.interviewOpportunityHandoff = null);
	}
	function w(e) {
		let t = (e.module ? f.querySelector(`.module-panel[data-module-page="${e.page}"][data-module="${e.module}"]:not(.is-filtered-out)`) : null)?.querySelector("h2, h3") || n("pageTitle");
		t && (t.tabIndex = -1, t.focus({ preventScroll: !0 }));
	}
	return {
		bindNavigation: m,
		renderPage: g,
		applyInitialRoute: _,
		filterModules: v,
		renderModule: y,
		navigate: b,
		jumpToModule: x,
		defaultModuleForPage: S,
		handleRouteTransition: C,
		focusCleanedRoute: w
	};
}
//#endregion
//#region frontend/src/shell/topbar-controller.ts
var dn = {
	glm: [["智谱开放平台", "https://open.bigmodel.cn/"], ["API Key 管理", "https://open.bigmodel.cn/apikey/platform"]],
	deepseek: [["DeepSeek 平台", "https://platform.deepseek.com/"], ["API Keys", "https://platform.deepseek.com/api_keys"]],
	kimi: [["Moonshot 控制台", "https://platform.moonshot.cn/"], ["API Key 管理", "https://platform.moonshot.cn/console/api-keys"]]
};
function fn(e) {
	let { state: t, request: n, ui: r, careerForm: i, loadQuestions: a, afterCareerGoalSaved: o, storage: s = localStorage, documentObject: c = document } = e, l = (e) => r.byId(e), u = !1;
	function d() {
		return l("careerProfileSelect")?.value || t.careerProfile || "tech";
	}
	function f(e = d()) {
		return t.careerProfiles.find((t) => t.id === e)?.label || "计算机 / 软件 / AI";
	}
	function p() {
		let e = d(), t = l("flowProfileLabel");
		t && (t.textContent = f(e));
		let n = {
			tech: "软件测试工程师 / AI 应用测试",
			ops: "新媒体运营 / 用户运营",
			marketing: "市场专员 / 商务拓展",
			finance: "财务助理 / 会计实习生",
			education: "学科教师 / 教务助理",
			hr: "人事行政专员 / 招聘助理"
		}, r = n[e] || n.tech;
		for (let e of [
			"analysisJobTitle",
			"jobTitleInput",
			"interviewJobTitle",
			"professionalJobTitle"
		]) {
			let t = l(e);
			t && (t.placeholder = `目标岗位，例如：${r}`);
		}
		l("professionalCategory")?.value === "career" && l("questionCategory")?.value === "career" && a("career");
	}
	async function m() {
		let e = await n("/career/profiles");
		t.careerProfiles = e.success ? e.profiles : [];
		let i = l("careerProfileSelect");
		i && (i.innerHTML = t.careerProfiles.map((e) => `<option value="${e.id}">${r.escapeHtml(e.label)}</option>`).join(""), i.value = t.careerProfiles.some((e) => e.id === t.careerProfile) ? t.careerProfile : e.default || "tech", t.careerProfile = i.value, s.setItem("jobhunter_career_profile", t.careerProfile), p());
	}
	async function h() {
		let e = await i.loadProfile({
			request: () => n("/profile"),
			controls: {
				role: l("careerGoalRole"),
				cities: l("careerGoalCities"),
				salaryMin: l("careerGoalSalaryMin"),
				salaryMax: l("careerGoalSalaryMax"),
				skills: l("careerGoalSkills"),
				direction: l("careerProfileSelect"),
				status: l("careerGoalStatus"),
				retry: l("retryCareerGoalBtn")
			},
			state: t
		});
		e.ok && e.direction.matched && (s.setItem("jobhunter_career_profile", t.careerProfile), p());
	}
	function g(e) {
		return i.parseList(l(e)?.value || "");
	}
	function _(e) {
		let t = l(e)?.value.trim() || "";
		return t === "" ? null : Number(t);
	}
	async function v(e) {
		e.preventDefault();
		let t = l("careerGoalRole"), a = t?.value.trim() || "", s = _("careerGoalSalaryMin"), c = _("careerGoalSalaryMax"), u = l("careerGoalStatus");
		if (!a) {
			u && (u.textContent = "请填写目标岗位。"), t?.focus();
			return;
		}
		if (s !== null && c !== null && s > c) {
			u && (u.textContent = "薪资下限不能高于上限。"), l("careerGoalSalaryMin")?.focus();
			return;
		}
		await i.saveProfile({
			request: (e) => n("/profile", {
				method: "PUT",
				body: e
			}),
			payload: {
				career_direction: d(),
				target_role: a,
				cities: g("careerGoalCities"),
				salary: {
					min: s,
					max: c
				},
				confirmed_skills: g("careerGoalSkills"),
				source_metadata: { form: "career-goal-editor" }
			},
			status: u,
			onSuccess: async () => {
				r.toast("求职目标档案已保存"), await o();
			}
		});
	}
	function y() {
		let e = l("soundToggleBtn");
		e && (e.classList.toggle("is-off", !t.soundEnabled), e.title = t.soundEnabled ? "关闭界面音效" : "开启界面音效", e.innerHTML = `<i data-lucide="${t.soundEnabled ? "volume-2" : "volume-x"}"></i>`, r.renderIcons());
	}
	function b(e) {
		let t = dn[e] || [], n = l("providerLinkList");
		n && (n.innerHTML = t.map(([e, t]) => `<a href="${t}" target="_blank" rel="noreferrer">${e}</a>`).join("") || "<span class=\"muted-note\">选择厂商后显示 API 获取入口。</span>");
	}
	function x() {
		let e = l("customModelInput"), t = l("modelSelect");
		if (!e || !t) return;
		let n = t.value === "custom";
		e.classList.toggle("hidden", !n), n || (e.value = "");
	}
	function S(e, n = "") {
		let r = t.providers.find((t) => t.id === e), i = l("modelSelect");
		if (!i) return;
		if (!r) {
			i.innerHTML = "";
			return;
		}
		let a = n || r.default_model || r.model;
		i.innerHTML = (r.models || []).map((e) => `<option value="${e.id}" ${e.id === a ? "selected" : ""}>${e.name}</option>`).join("") + "<option value=\"custom\">自定义模型 ID...</option>", x();
	}
	async function C() {
		let e = await n("/config/ai-status");
		if (!e.success) return;
		t.providers = e.providers || [];
		let r = l("providerSelect");
		r && (r.innerHTML = t.providers.map((t) => `<option value="${t.id}" ${t.id === e.provider ? "selected" : ""}>${t.name}</option>`).join("")), S(e.provider, e.selected_model || e.model), b(e.provider);
		let i = l("providerName"), a = l("providerModel"), o = l("agentModeLabel"), s = l("agentModeDetail"), c = l("providerDot");
		i && (i.textContent = e.ai_enabled ? e.provider_name : "本地兜底"), a && (a.textContent = e.ai_enabled ? e.model : "规则引擎可用"), o && (o.textContent = e.ai_enabled ? `${e.provider_name} 已连接` : "本地智能求职助手"), s && (s.textContent = e.ai_enabled ? "本地任务优先执行；开放问题由模型增强，写入仍需你确认。" : "本地任务可直接执行；开放问题与完整简历深度改写需配置模型。"), c && (c.style.background = e.ai_enabled ? "var(--mint)" : "var(--yellow)");
	}
	async function w() {
		let e = l("providerSelect")?.value || "", t = l("modelSelect")?.value || "";
		if (t === "custom" && (t = l("customModelInput")?.value.trim() || "", !t)) {
			r.toast("请输入自定义模型 ID，例如 deepseek-chat、kimi-k2.6");
			return;
		}
		let i = l("apiKeyInput"), a = i?.value.trim() || "", o = await n("/config/ai-key", {
			method: "POST",
			body: {
				provider: e,
				model: t,
				api_key: a
			}
		});
		o.success && (i && (i.value = ""), r.toast(a ? `已保存并启用 ${o.provider} / ${o.model}` : "已切换模型；未填 Key 时使用本地兜底"), await C());
	}
	function T(e) {
		t.theme = e, s.setItem("jobhunter_theme", e), c.body.dataset.theme = e, c.querySelectorAll("[data-theme-choice]").forEach((t) => {
			t.classList.toggle("active", t.dataset.themeChoice === e);
		});
		let n = e === "anime" ? "%20(2)" : "", r = {
			brandLogo: `/assets/images/logo${n}.png`,
			heroImage: `/assets/images/hero-bg${n}.png`,
			dashboardImage: `/assets/images/dashboard${n}.png`,
			resumeImage: `/assets/images/resume-analysis${n}.png`,
			jobMatchImage: `/assets/images/job-match${n}.png`,
			interviewImage: `/assets/images/interview-scene${n}.png`,
			interviewAvatar: `/assets/images/ai-avatar${n}.png`,
			trackImage: `/assets/images/application-track${n}.png`,
			coachAvatar: `/assets/images/ai-avatar${n}.png`
		}, i = {
			resumeImage: "center 42%",
			interviewImage: "center 42%",
			trackImage: "center 72%",
			dashboardImage: "center"
		};
		Object.entries(r).forEach(([e, t]) => {
			let n = l(e);
			n && (n.src = t, e in i && (n.parentElement?.style.setProperty("--asset-bg", `url("${t}")`), n.parentElement?.style.setProperty("--asset-pos", i[e])));
		});
		let a = l("loadingVideo");
		a && (a.src = `/assets/images/loading${e === "anime" ? "%20(2)" : ""}.mp4`);
	}
	function ee() {
		u || (u = !0, y(), l("modelConfigBtn")?.addEventListener("click", () => {
			r.playTone("tap"), l("modelConfigPanel")?.classList.toggle("hidden");
		}), l("soundToggleBtn")?.addEventListener("click", () => {
			t.soundEnabled = !t.soundEnabled, s.setItem("jobhunter_sound", t.soundEnabled ? "on" : "off"), y(), t.soundEnabled && r.playTone("success"), r.toast(t.soundEnabled ? "界面音效已开启" : "界面音效已关闭", { silent: !0 });
		}), l("closeModelPanel")?.addEventListener("click", () => l("modelConfigPanel")?.classList.add("hidden")), l("saveProviderBtn")?.addEventListener("click", () => void w()), l("providerSelect")?.addEventListener("change", (e) => {
			let t = e.currentTarget.value;
			S(t), b(t);
		}), l("modelSelect")?.addEventListener("change", x), c.querySelectorAll("[data-theme-choice]").forEach((e) => {
			e.addEventListener("click", () => {
				r.playTone("tap"), T(e.dataset.themeChoice || "glass");
			});
		}), l("careerProfileSelect")?.addEventListener("change", (e) => {
			t.careerProfile = e.currentTarget.value || "tech", s.setItem("jobhunter_career_profile", t.careerProfile), p(), a(l("questionCategory")?.value || "general"), r.toast(`已切换求职方向：${f(t.careerProfile)}`);
		}), l("careerGoalForm")?.addEventListener("submit", (e) => {
			v(e);
		}), l("retryCareerGoalBtn")?.addEventListener("click", () => void h()));
	}
	async function te() {
		T(t.theme), await m(), await h(), await C();
	}
	return {
		bind: ee,
		initialize: te,
		selectedCareerProfile: d,
		careerProfileLabel: f,
		applyTheme: T
	};
}
//#endregion
//#region frontend/src/app/runtime.ts
var pn = an({
	location: window.location,
	runtimeConfig: window.__JOBHUNTER_CONFIG__
}), mn = 1, hn = `jobhunter_agent_conversation_${mn}`, gn = sn({ baseUrl: pn }), I = {
	resumes: [],
	providers: [],
	careerProfiles: [],
	careerProfile: localStorage.getItem("jobhunter_career_profile") || "tech",
	activeInterview: null,
	interviewStageIndex: 0,
	pendingInterviewSubmission: null,
	interviewSubmitting: !1,
	currentInterviewSession: null,
	skillChart: null,
	recognition: null,
	speechController: null,
	recognizing: !1,
	currentPracticeCategory: "general",
	theme: localStorage.getItem("jobhunter_theme") || "glass",
	editingResumeId: null,
	editingAppId: null,
	applicationStatuses: [],
	currentOpportunityId: null,
	currentOpportunityWorkspace: null,
	opportunityLoadGeneration: 0,
	pendingApplicationHandoff: null,
	interviewOpportunityHandoff: null,
	matchOpportunityId: null,
	opportunityOpener: null,
	applications: [],
	recordingController: null,
	audioBlob: null,
	audioMetrics: null,
	soundEnabled: localStorage.getItem("jobhunter_sound") !== "off",
	audioContext: null,
	agentConversationId: localStorage.getItem(hn) || "",
	agentDrawerOpener: null,
	agentProposals: /* @__PURE__ */ new Map(),
	agentProposalEpochs: /* @__PURE__ */ new Map(),
	agentProposalMutationEpoch: 0,
	agentConversationProposalIds: /* @__PURE__ */ new Set(),
	agentCommandProposalIds: /* @__PURE__ */ new Set(),
	currentPage: "home",
	currentModule: ""
}, _n = cn(I), L = (e) => _n.byId(e), { downloadBlob: vn, downloadResponse: yn, escapeHtml: bn, playTone: xn, renderIcons: Sn, renderText: Cn, toast: wn, withLoading: Tn } = _n, En = {
	home: "项目总览",
	resume: "简历实验室",
	interview: "面试训练场",
	tracker: "投递看板",
	agent: "求职指挥台"
}, Dn = fn({
	state: I,
	request: gn,
	ui: _n,
	careerForm: Je,
	loadQuestions: (e) => Wn.loadQuestions(e),
	afterCareerGoalSaved: async () => {
		await Kn.loadDashboard(), An.syncContext();
	}
}), { selectedCareerProfile: On, careerProfileLabel: kn } = Dn, An, jn = fe({
	userId: mn,
	conversationStorageKey: hn,
	state: I,
	request: gn,
	ui: _n,
	contextualAgent: pe,
	contextPayload: () => An.contextPayload(),
	openDrawer: (e) => An.openDrawer(e),
	closeDrawer: () => An.closeDrawer(),
	navigate: (e, t) => Hn.jumpToModule(e, t),
	loadResumes: () => Un.load(),
	loadApplications: () => Kn.loadApplications(),
	loadDashboard: () => Kn.loadDashboard(),
	loadOpportunityWorkspace: (e, t) => Kn.loadWorkspace(e, t),
	syncAgentContext: () => An.syncContext()
}), { clearConversation: Mn, createConversation: Nn, focusResultFromLocation: Pn, generateCareerReport: Fn, handleChatLogClick: In, loadCommandCenter: Ln, loadConversations: Rn, openProposal: zn, renderCommandOpportunities: Bn, sendMessage: Vn } = jn;
An = A({
	state: I,
	byId: L,
	contextualAgent: pe,
	escapeHtml: bn,
	escapeAttr: _t,
	renderIcons: Sn,
	loadCommandCenter: () => jn.loadCommandCenter(),
	documentObject: document,
	windowObject: window
});
var Hn = un({
	state: I,
	byId: L,
	history: () => Gn,
	playTone: xn,
	syncAgentContext: () => An.syncContext(),
	loadAgentCommandCenter: () => jn.loadCommandCenter(),
	routeLeavesFlow: nn,
	clearApplicationHandoff: Wi,
	clearMatchOpportunityLink: Gi,
	pageTitles: En,
	windowObject: window,
	documentObject: document
}), Un = rn({
	userId: mn,
	apiBaseUrl: pn,
	state: I,
	request: gn,
	byId: L,
	escapeHtml: bn,
	renderText: Cn,
	toast: wn,
	withLoading: Tn,
	renderIcons: Sn,
	syncAgentContext: () => An.syncContext(),
	jumpToModule: (e, t) => Hn.jumpToModule(e, t),
	closeAgentDrawer: () => An.closeDrawer(),
	selectedCareerProfile: On,
	careerProfileLabel: kn,
	loadDashboard: () => Kn.loadDashboard(),
	clearMatchOpportunityLink: Gi,
	buildMatchPayload: tn,
	downloadResponse: yn
}), Wn = Ct({
	userId: mn,
	apiBaseUrl: pn,
	state: I,
	request: gn,
	byId: L,
	escapeHtml: bn,
	renderText: Cn,
	toast: wn,
	withLoading: Tn,
	renderIcons: Sn,
	selectedCareerProfile: On,
	loadDashboard: () => Kn.loadDashboard(),
	buildInterviewStartPayload: Qt,
	downloadBlob: vn,
	downloadResponse: yn,
	confirmAction: (e) => window.confirm(e),
	submission: Ft,
	media: wt,
	capabilities: tt
}), Gn = Jt({
	window,
	defaultModule: Hn.defaultModuleForPage,
	onRouteTransition: Hn.handleRouteTransition,
	focusRoute: Hn.focusCleanedRoute,
	showPage: (e) => {
		L(`page-${e}`) && Hn.renderPage(e);
	},
	showModule: Hn.renderModule,
	loadWorkspace: (e, t) => Kn.loadWorkspace(e, t),
	closeWorkspace: (e) => Kn.resetWorkspace(e),
	notifyStale: () => wn("机会详情不存在或已删除，链接已重置。"),
	notifyForbidden: () => wn("无权访问该机会详情，链接已重置。"),
	notifyRetryable: () => {
		I.currentOpportunityId && Kn.showWorkspaceError(I.currentOpportunityId, "机会详情暂时无法加载，请稍后重试。");
	}
}), Kn = Kt({
	userId: mn,
	state: I,
	request: gn,
	byId: L,
	escapeHtml: bn,
	renderText: Cn,
	toast: wn,
	withLoading: Tn,
	renderIcons: Sn,
	syncAgentContext: () => An.syncContext(),
	jumpToModule: (e, t) => Hn.jumpToModule(e, t),
	filterModules: (e, t, n) => Hn.filterModules(e, t, n),
	renderAgentCommandOpportunities: Bn,
	applicationPayloadForJob: en,
	buildInterviewHandoff: Zt,
	renderApplicationHandoffNotice: Ui,
	clearApplicationHandoff: Wi,
	renderMatchOpportunityNotice: Ki,
	openOriginalResume: (e) => Un.openOriginal(e),
	fillResume: (e) => Un.fill(e),
	openInterviewRoom: (e) => Wn.openRoom(e),
	parseFeedbackSummary: (e) => Wn.parseFeedbackSummary(e),
	confirmAction: (e) => window.confirm(e),
	history: Gn
}), { applyInitialRoute: qn, bindNavigation: Jn, filterModules: Yn, jumpToModule: Xn, navigate: Zn } = Hn, { analyze: Qn, analyzeJd: $n, auditSelected: er, cancelEdit: tr, convertDocument: nr, export: rr, fill: ir, fillTitleFromFile: ar, generate: or, improveSelected: sr, load: cr, match: lr, openOriginal: ur, remove: dr, renderSkills: fr, replaceOriginal: pr, save: mr, selectedResumeId: hr, selectedTailorId: gr, tailor: _r } = Un, { analyzeRecordedAudio: vr, analyzeVoice: yr, applyBrowserCapabilities: br, categoryName: xr, clearTrainingRecords: Sr, computeAudioMetrics: Cr, deleteTrainingRecord: wr, downloadSavedAudio: Tr, extensionFromMime: Er, formatDate: Dr, getRecordingController: Or, handleAudioUpload: kr, loadProfessionalPack: Ar, loadQuestions: jr, loadTrainingRecords: Mr, openRoom: Nr, parseFeedbackSummary: Pr, renderAudioPreview: Fr, renderConversation: Ir, renderFeedback: Lr, renderFeedbackHtml: Rr, renderRecordColumn: zr, renderRecordDetail: Br, safeJson: Vr, scorePractice: Hr, scoreProfessionalAnswer: Ur, selectProfessionalQuestion: Wr, selectQuestion: Gr, sendAnswer: Kr, sendRoomAnswer: qr, setupSpeechRecognition: Jr, showProfessionalReference: Yr, showSampleAnswer: Xr, stageName: Zr, start: Qr, startAudioRecording: $r, stopAudioRecording: ei, toggleVoiceInput: ti, updateQuestion: ni, viewTrainingRecord: ri } = Wn, { advanceApplication: ii, closeWorkspace: ai, coachApplication: oi, continueInterview: si, deleteApplication: ci, editApplication: li, evaluateSalary: ui, handleTabKeydown: di, loadApplications: fi, loadDashboard: pi, loadWorkspace: mi, openWorkspace: hi, openWorkspaceResume: gi, prepareInterview: _i, renderCareerPulse: vi, renderMatch: yi, renderNextActions: bi, renderOverview: xi, renderResume: Si, renderTimeline: Ci, renderWorkspace: wi, resetWorkspace: Ti, retryWorkspace: Ei, saveApplication: Di, selectTab: Oi, showWorkspaceError: ki, useWorkspaceJd: Ai, workspaceDate: ji } = Kn, { closeDrawer: Mi, currentResumeId: Ni, handleDrawerKeydown: Pi, openDrawer: R, renderContextChips: z, syncContext: Fi } = An;
document.addEventListener("DOMContentLoaded", async () => {
	Gn.bind(), Jn(), Ii(), br(), Jr(), await Dn.initialize(), await Promise.all([
		cr(),
		pi(),
		fi(),
		jr(),
		Mr()
	]), await Rn(), await qn(), await Ln(), await Pn(), Fi(), Sn();
});
function Ii() {
	An.bind(), Dn.bind(), document.addEventListener("click", zi), document.addEventListener("change", Ri), document.querySelectorAll("[data-flow-jump]").forEach((e) => {
		e.addEventListener("click", () => {
			let [t, n] = (e.dataset.flowJump || "").split(":");
			xn("jump"), Xn(t, n);
		});
	}), document.querySelectorAll("[data-section-filter]").forEach((e) => {
		e.addEventListener("click", () => {
			let [t, n] = (e.dataset.sectionFilter || "").split(":");
			xn("tap"), Zn(t, n);
		});
	}), document.querySelectorAll(".page-subnav").forEach((e) => {
		let t = e.querySelector("[data-section-filter]");
		if (t) {
			let [e, n] = (t.dataset.sectionFilter || "").split(":");
			Yn(e, n, t);
		}
	}), L("refreshResumesBtn").addEventListener("click", cr), L("saveResumeBtn").addEventListener("click", mr), L("cancelResumeEditBtn")?.addEventListener("click", tr), L("generateResumeBtn").addEventListener("click", or), L("exportPdfBtn").addEventListener("click", () => rr("pdf")), L("exportWordBtn").addEventListener("click", () => rr("word")), L("pdfToWordFile").addEventListener("change", () => nr("pdf-to-word", "pdfToWordFile")), L("wordToPdfFile").addEventListener("change", () => nr("word-to-pdf", "wordToPdfFile")), L("tailorBtn").addEventListener("click", _r), L("matchBtn").addEventListener("click", lr), L("analyzeJdBtn").addEventListener("click", $n), L("resumeAuditBtn").addEventListener("click", er), L("resumeImproveBtn").addEventListener("click", sr), L("skillsBtn").addEventListener("click", fr), L("startInterviewBtn").addEventListener("click", Qr), L("sendAnswerBtn").addEventListener("click", Kr), L("roomSubmitBtn").addEventListener("click", qr), L("closeInterviewRoom").addEventListener("click", () => L("interviewRoom").classList.add("hidden")), L("roomVoiceCopyBtn").addEventListener("click", () => {
		L("answerInput").value = L("roomAnswer").value, L("interviewRoom").classList.add("hidden"), Xn("interview", "mock"), L("answerInput").focus();
	}), L("analyzeVoiceBtn").addEventListener("click", yr), L("voiceBtn").addEventListener("click", ti), L("recordAudioBtn").addEventListener("click", () => $r("answer")), L("stopAudioBtn").addEventListener("click", ei), L("analyzeAudioBtn").addEventListener("click", () => vr("answer")), L("audioFileInput").addEventListener("change", kr), L("roomRecordBtn").addEventListener("click", () => $r("room")), L("roomStopRecordBtn").addEventListener("click", ei), L("roomAnalyzeAudioBtn").addEventListener("click", () => vr("room")), L("loadQuestionsBtn").addEventListener("click", () => jr(L("questionCategory").value)), L("questionCategory").addEventListener("change", () => jr(L("questionCategory").value)), L("scorePracticeBtn").addEventListener("click", Hr), L("professionalPackBtn").addEventListener("click", Ar), L("scoreProfessionalBtn").addEventListener("click", Ur), L("clearTrainingRecordsBtn").addEventListener("click", Sr), L("saveAppBtn").addEventListener("click", Di), L("clearApplicationHandoff")?.addEventListener("click", Wi), L("clearMatchOpportunityLink")?.addEventListener("click", Gi), L("appJob")?.addEventListener("input", () => {
		I.pendingApplicationHandoff && !Object.keys(en(I.pendingApplicationHandoff, L("appJob").value)).length && Wi();
	}), L("closeOpportunityWorkspace")?.addEventListener("click", ai), document.querySelectorAll(".opportunity-tabs [role=\"tab\"]").forEach((e) => {
		e.addEventListener("click", () => Oi(e)), e.addEventListener("keydown", (e) => {
			di(e);
		});
	}), L("salaryBtn").addEventListener("click", ui), L("chatLog")?.addEventListener("click", In), L("agentResumeUpload")?.addEventListener("click", Bi), L("sendAgentBtn").addEventListener("click", () => Vn()), L("careerReportBtn").addEventListener("click", Fn), L("newAgentConversation")?.addEventListener("click", () => Nn()), L("clearAgentConversation")?.addEventListener("click", Mn), L("agentConversationSelect")?.addEventListener("change", async () => {
		I.agentConversationId = L("agentConversationSelect").value, localStorage.setItem(hn, I.agentConversationId), await jn.loadConversations(I.agentConversationId, !0);
	}), L("agentInput").addEventListener("keydown", (e) => {
		e.key === "Enter" && !e.shiftKey && (e.preventDefault(), Vn());
	}), L("resumeFile")?.addEventListener("change", ar), document.querySelectorAll("[data-prompt]").forEach((e) => {
		e.addEventListener("click", () => {
			L("agentInput").value = e.dataset.prompt, Vn();
		});
	});
}
function Li(e) {
	let t = Number(e);
	return Number.isInteger(t) && t > 0 ? t : null;
}
function Ri(e) {
	let t = e.target instanceof HTMLInputElement ? e.target.closest("[data-command-change]") : null;
	if (!t || t.dataset.commandChange !== "resume-replace-original") return;
	let n = Li(t.dataset.resumeId);
	n && pr(n, t);
}
function zi(e) {
	let t = e.target instanceof Element ? e.target.closest("[data-command], [data-route-page]") : null;
	if (!(t instanceof HTMLElement)) return;
	let n = t.dataset.routePage;
	if (n) {
		Xn(n, t.dataset.routeModule || "");
		return;
	}
	let r = t.dataset.command;
	if (!r) return;
	let i = Li(t.dataset.resumeId), a = Li(t.dataset.opportunityId), o = Li(t.dataset.recordId), s = Li(t.dataset.sessionId), c = Li(t.dataset.actionId), l = Li(t.dataset.proposalId), u = {
		"resume-edit": () => i && ir(i),
		"resume-open-original": () => i && ur(i),
		"resume-analyze": () => i && Qn(i),
		"resume-delete": () => i && dr(i),
		"resume-improve-selected": sr,
		"resume-tailor": _r,
		"prepare-interview-from-jd": Vi,
		"prepare-application-from-jd": Hi,
		"interview-select-question": () => Gr(t.dataset.question || "", t.dataset.category || "general"),
		"interview-show-sample": () => Xr(t.dataset.answer || ""),
		"training-view": () => o && ri(t.dataset.recordType || "", o),
		"training-delete": () => o && wr(t.dataset.recordType || "", o),
		"training-audio-download": () => Tr(t.dataset.audioFile || "", t.dataset.audioFormat || "wav"),
		"interview-select-professional": () => Wr(t.dataset.question || ""),
		"interview-show-professional-reference": () => Yr(t.dataset.reference || ""),
		"opportunity-open": () => a && hi(a),
		"opportunity-refresh": () => a && hi(a, { updateUrl: !1 }),
		"opportunity-retry": () => a && Ei(a),
		"opportunity-edit": () => a && li(a),
		"opportunity-delete": () => a && ci(a),
		"opportunity-coach": () => a && oi(a),
		"opportunity-advance": () => a && ii(a),
		"opportunity-use-jd": Ai,
		"opportunity-open-resume": () => i && gi(i, t.dataset.hasOriginal === "true"),
		"opportunity-continue-interview": () => s && si(s),
		"opportunity-prepare-interview": () => _i(c),
		"agent-command-retry": Ln,
		"agent-proposal-open": () => l && zn(l, t),
		"agent-opportunity-open": () => {
			Mi(), a && hi(a);
		},
		"agent-result-retry": Pn
	}[r];
	u && u();
}
function Bi() {
	return tr(), Un.openUploadFromAgent();
}
function Vi() {
	I.interviewOpportunityHandoff = null, L("interviewJobTitle").value = L("jobTitleInput").value || L("interviewJobTitle").value, L("interviewJd").value = L("jdInput").value || L("interviewJd").value, L("interviewResumeSelect").value = gr() || hr() || "", Xn("interview", "mock"), wn("已把岗位信息带入模拟面试");
}
function Hi() {
	let e = L("jobTitleInput").value || L("appJob").value;
	I.pendingApplicationHandoff = $t({
		jobTitle: e,
		jd: L("jdInput").value.trim(),
		resumeId: gr() || hr()
	}), L("appJob").value = e, L("appNotes").value = L("jdInput").value ? `JD 摘要：${L("jdInput").value.slice(0, 180)}` : L("appNotes").value, Ui(), Xn("tracker", "add"), wn("已带入岗位信息，补公司名后即可保存投递");
}
function Ui() {
	let e = I.pendingApplicationHandoff;
	if (L("applicationHandoffNotice")?.classList.toggle("hidden", !e), !e || !L("applicationHandoffContext")) return;
	let t = I.resumes.find((t) => t.id === e.resumeId)?.title || "未关联简历";
	L("applicationHandoffContext").textContent = `${e.jobTitle} · ${t}${e.jd ? " · 已带入 JD" : ""}`;
}
function Wi() {
	I.pendingApplicationHandoff = null, Ui();
}
function Gi() {
	I.matchOpportunityId = null, Ki();
}
function Ki() {
	let e = I.matchOpportunityId;
	L("matchOpportunityNotice")?.classList.toggle("hidden", !e), e && L("matchOpportunityContext") && (L("matchOpportunityContext").textContent = `机会 #${e}`);
}
//#endregion
//#region frontend/src/app/main.tsx
var qi = document.getElementById("reactAppRoot");
if (!qi) throw Error("Missing React composition root: #reactAppRoot");
var Ji = (0, p.createRoot)(qi);
(0, f.flushSync)(() => {
	Ji.render(/* @__PURE__ */ (0, D.jsx)(d.StrictMode, { children: /* @__PURE__ */ (0, D.jsx)(O, {}) }));
});
//#endregion
