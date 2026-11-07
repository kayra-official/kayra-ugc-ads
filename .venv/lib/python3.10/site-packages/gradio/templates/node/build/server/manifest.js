const manifest = (() => {
function __memo(fn) {
	let value;
	return () => value ??= (value = fn());
}

return {
	appDir: "_app",
	appPath: "_app",
	assets: new Set([]),
	mimeTypes: {},
	_: {
		client: {start:"_app/immutable/entry/start.BQvdY2SS.js",app:"_app/immutable/entry/app.DP16-hrj.js",imports:["_app/immutable/entry/start.BQvdY2SS.js","_app/immutable/chunks/CACz_rEZ.js","_app/immutable/chunks/WS1bLMZz.js","_app/immutable/chunks/C_df6e1L.js","_app/immutable/entry/app.DP16-hrj.js","_app/immutable/chunks/WS1bLMZz.js","_app/immutable/chunks/C_df6e1L.js","_app/immutable/chunks/Bocc91eC.js","_app/immutable/chunks/C5-g0Q-M.js"],stylesheets:[],fonts:[],uses_env_dynamic_public:false},
		nodes: [
			__memo(() => import('./chunks/0-DQalbqlr.js')),
			__memo(() => import('./chunks/1-T52oa6gQ.js')),
			__memo(() => import('./chunks/2-CwMpezk3.js').then(function (n) { return n.a3; }))
		],
		remotes: {
			
		},
		routes: [
			{
				id: "/[...catchall]",
				pattern: /^(?:\/([^]*))?\/?$/,
				params: [{"name":"catchall","optional":false,"rest":true,"chained":true}],
				page: { layouts: [0,], errors: [1,], leaf: 2 },
				endpoint: null
			}
		],
		prerendered_routes: new Set([]),
		matchers: async () => {
			
			return {  };
		},
		server_assets: {}
	}
}
})();

const prerendered = new Set([]);

const base = "";

export { base, manifest, prerendered };
//# sourceMappingURL=manifest.js.map
