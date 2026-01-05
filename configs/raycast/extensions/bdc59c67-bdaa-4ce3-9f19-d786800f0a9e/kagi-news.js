"use strict";var $e=Object.create;var j=Object.defineProperty;var we=Object.getOwnPropertyDescriptor;var ke=Object.getOwnPropertyNames;var xe=Object.getPrototypeOf,ve=Object.prototype.hasOwnProperty;var Se=(e,t)=>{for(var n in t)j(e,n,{get:t[n],enumerable:!0})},X=(e,t,n,r)=>{if(t&&typeof t=="object"||typeof t=="function")for(let o of ke(t))!ve.call(e,o)&&o!==n&&j(e,o,{get:()=>t[o],enumerable:!(r=we(t,o))||r.enumerable});return e};var B=(e,t,n)=>(n=e!=null?$e(xe(e)):{},X(t||!e||!e.__esModule?j(n,"default",{value:e,enumerable:!0}):n,e)),Ee=e=>X(j({},"__esModule",{value:!0}),e);var Ne={};Se(Ne,{default:()=>ge});module.exports=Ee(Ne);var h=require("@raycast/api");var u=B(require("react")),g=require("@raycast/api");var ee=Object.prototype.hasOwnProperty;function G(e,t){var n,r;if(e===t)return!0;if(e&&t&&(n=e.constructor)===t.constructor){if(n===Date)return e.getTime()===t.getTime();if(n===RegExp)return e.toString()===t.toString();if(n===Array){if((r=e.length)===t.length)for(;r--&&G(e[r],t[r]););return r===-1}if(!n||typeof e=="object"){r=0;for(n in e)if(ee.call(e,n)&&++r&&!ee.call(t,n)||!(n in t)||!G(e[n],t[n]))return!1;return Object.keys(t).length===r}}return e!==e&&t!==t}var D=B(require("node:fs")),K=B(require("node:path")),ae=B(require("node:crypto"));var se=require("react/jsx-runtime");function Ae(e){let t=(0,u.useRef)(e),n=(0,u.useRef)(0);return G(e,t.current)||(t.current=e,n.current+=1),(0,u.useMemo)(()=>t.current,[n.current])}function S(e){let t=(0,u.useRef)(e);return t.current=e,t}function _e(e,t){let n=e instanceof Error?e.message:String(e);return(0,g.showToast)({style:g.Toast.Style.Failure,title:t?.title??"Something went wrong",message:t?.message??n,primaryAction:t?.primaryAction??te(e),secondaryAction:t?.primaryAction?te(e):void 0})}var te=e=>{let t=!0,n="[Extension Name]...",r="";try{let s=JSON.parse((0,D.readFileSync)((0,K.join)(g.environment.assetsPath,"..","package.json"),"utf8"));n=`[${s.title}]...`,r=`https://raycast.com/${s.owner||s.author}/${s.name}`,(!s.owner||s.access==="public")&&(t=!1)}catch{}let o=g.environment.isDevelopment||t,l=e instanceof Error?e?.stack||e?.message||"":String(e);return{title:o?"Copy Logs":"Report Error",onAction(s){s.hide(),o?g.Clipboard.copy(l):(0,g.open)(`https://github.com/raycast/extensions/issues/new?&labels=extension%2Cbug&template=extension_bug_report.yml&title=${encodeURIComponent(n)}&extension-url=${encodeURI(r)}&description=${encodeURIComponent(`#### Error:
\`\`\`
${l}
\`\`\`
`)}`)}}};function Re(e,t,n){let r=(0,u.useRef)(0),[o,l]=(0,u.useState)({isLoading:!0}),s=S(e),a=S(n?.abortable),i=S(t||[]),d=S(n?.onError),p=S(n?.onData),c=S(n?.onWillExecute),$=S(n?.failureToastOptions),v=S(o.data),k=(0,u.useRef)(null),f=(0,u.useRef)({page:0}),w=(0,u.useRef)(!1),A=(0,u.useRef)(!0),P=(0,u.useRef)(50),x=(0,u.useCallback)(()=>(a.current&&(a.current.current?.abort(),a.current.current=new AbortController),++r.current),[a]),y=(0,u.useCallback)((...C)=>{let E=x();c.current?.(C),l(m=>({...m,isLoading:!0}));let L=Pe(s.current)(...C);function M(m){return m.name=="AbortError"||E===r.current&&(d.current?d.current(m):g.environment.launchType!==g.LaunchType.Background&&_e(m,{title:"Failed to fetch latest data",primaryAction:{title:"Retry",onAction(U){U.hide(),k.current?.(...i.current||[])}},...$.current}),l({error:m,isLoading:!1})),m}return typeof L=="function"?(w.current=!0,L(f.current).then(({data:m,hasMore:U,cursor:be})=>(E===r.current&&(f.current&&(f.current.cursor=be,f.current.lastItem=m?.[m.length-1]),p.current&&p.current(m,f.current),U&&(P.current=m.length),A.current=U,l(ye=>f.current.page===0?{data:m,isLoading:!1}:{data:(ye.data||[])?.concat(m),isLoading:!1})),m),m=>(A.current=!1,M(m)))):(w.current=!1,L.then(m=>(E===r.current&&(p.current&&p.current(m),l({data:m,isLoading:!1})),m),M))},[p,d,i,s,l,k,c,f,$,x]);k.current=y;let _=(0,u.useCallback)(()=>{f.current={page:0};let C=i.current||[];return y(...C)},[y,i]),R=(0,u.useCallback)(async(C,E)=>{let L;try{if(E?.optimisticUpdate){x(),typeof E?.rollbackOnError!="function"&&E?.rollbackOnError!==!1&&(L=structuredClone(v.current?.value));let M=E.optimisticUpdate;l(m=>({...m,data:M(m.data)}))}return await C}catch(M){if(typeof E?.rollbackOnError=="function"){let m=E.rollbackOnError;l(U=>({...U,data:m(U.data)}))}else E?.optimisticUpdate&&E?.rollbackOnError!==!1&&l(m=>({...m,data:L}));throw M}finally{E?.shouldRevalidateAfter!==!1&&(g.environment.launchType===g.LaunchType.Background||g.environment.commandMode==="menu-bar"?await _():_())}},[_,v,l,x]),T=(0,u.useCallback)(()=>{f.current.page+=1;let C=i.current||[];y(...C)},[f,i,y]);(0,u.useEffect)(()=>{f.current={page:0},n?.execute!==!1?y(...t||[]):x()},[Ae([t,n?.execute,y]),a,f]),(0,u.useEffect)(()=>()=>{x()},[x]);let W=n?.execute!==!1?o.isLoading:!1,z={...o,isLoading:W},F=w.current?{pageSize:P.current,hasMore:A.current,onLoadMore:T}:void 0;return{...z,revalidate:_,mutate:R,pagination:F}}function Pe(e){return e===Promise.all||e===Promise.race||e===Promise.resolve||e===Promise.reject?e.bind(Promise):e}function re(e){return typeof e!="function"?!1:/^function\s+\w*\s*\(\s*\)\s*{\s+\[native code\]\s+}$/i.exec(Function.prototype.toString.call(e))!==null}function Te(e){return e instanceof URLSearchParams?e.toString():e}function ie(e,t=[]){function n(r){return"update"in e?e.update(r,"utf8"):e.write(r)}return{dispatch:function(r){r=Te(r),r===null?this._null():this["_"+typeof r](r)},_object:function(r){let o=/\[object (.*)\]/i,l=Object.prototype.toString.call(r),s=o.exec(l)?.[1]??"unknown:["+l+"]";s=s.toLowerCase();let a=null;if((a=t.indexOf(r))>=0){this.dispatch("[CIRCULAR:"+a+"]");return}else t.push(r);if(Buffer.isBuffer(r))return n("buffer:"),n(r.toString("utf8"));if(s!=="object"&&s!=="function"&&s!=="asyncfunction")if(this["_"+s])this["_"+s](r);else throw new Error('Unknown object type "'+s+'"');else{let i=Object.keys(r);i=i.sort(),re(r)||i.splice(0,0,"prototype","__proto__","constructor"),n("object:"+i.length+":");let d=this;return i.forEach(function(p){d.dispatch(p),n(":"),d.dispatch(r[p]),n(",")})}},_array:function(r,o){o=typeof o<"u"?o:!1;let l=this;if(n("array:"+r.length+":"),!o||r.length<=1){r.forEach(function(i){l.dispatch(i)});return}let s=[],a=r.map(function(i){let d=Ce(),p=t.slice();return ie(d,p).dispatch(i),s=s.concat(p.slice(t.length)),d.read().toString()});t=t.concat(s),a.sort(),this._array(a,!1)},_date:function(r){n("date:"+r.toJSON())},_symbol:function(r){n("symbol:"+r.toString())},_error:function(r){n("error:"+r.toString())},_boolean:function(r){n("bool:"+r.toString())},_string:function(r){n("string:"+r.length+":"),n(r.toString())},_function:function(r){n("fn:"),re(r)?this.dispatch("[native]"):this.dispatch(r.toString()),this.dispatch("function-name:"+String(r.name)),this._object(r)},_number:function(r){n("number:"+r.toString())},_xml:function(r){n("xml:"+r.toString())},_null:function(){n("Null")},_undefined:function(){n("Undefined")},_regexp:function(r){n("regex:"+r.toString())},_uint8array:function(r){n("uint8array:"),this.dispatch(Array.prototype.slice.call(r))},_uint8clampedarray:function(r){n("uint8clampedarray:"),this.dispatch(Array.prototype.slice.call(r))},_int8array:function(r){n("int8array:"),this.dispatch(Array.prototype.slice.call(r))},_uint16array:function(r){n("uint16array:"),this.dispatch(Array.prototype.slice.call(r))},_int16array:function(r){n("int16array:"),this.dispatch(Array.prototype.slice.call(r))},_uint32array:function(r){n("uint32array:"),this.dispatch(Array.prototype.slice.call(r))},_int32array:function(r){n("int32array:"),this.dispatch(Array.prototype.slice.call(r))},_float32array:function(r){n("float32array:"),this.dispatch(Array.prototype.slice.call(r))},_float64array:function(r){n("float64array:"),this.dispatch(Array.prototype.slice.call(r))},_arraybuffer:function(r){n("arraybuffer:"),this.dispatch(new Uint8Array(r))},_url:function(r){n("url:"+r.toString())},_map:function(r){n("map:");let o=Array.from(r);this._array(o,!0)},_set:function(r){n("set:");let o=Array.from(r);this._array(o,!0)},_file:function(r){n("file:"),this.dispatch([r.name,r.size,r.type,r.lastModified])},_blob:function(){throw Error(`Hashing Blob objects is currently not supported
(see https://github.com/puleos/object-hash/issues/26)
Use "options.replacer" or "options.ignoreUnknown"
`)},_domwindow:function(){n("domwindow")},_bigint:function(r){n("bigint:"+r.toString())},_process:function(){n("process")},_timer:function(){n("timer")},_pipe:function(){n("pipe")},_tcp:function(){n("tcp")},_udp:function(){n("udp")},_tty:function(){n("tty")},_statwatcher:function(){n("statwatcher")},_securecontext:function(){n("securecontext")},_connection:function(){n("connection")},_zlib:function(){n("zlib")},_context:function(){n("context")},_nodescript:function(){n("nodescript")},_httpparser:function(){n("httpparser")},_dataview:function(){n("dataview")},_signal:function(){n("signal")},_fsevent:function(){n("fsevent")},_tlswrap:function(){n("tlswrap")}}}function Ce(){return{buf:"",write:function(e){this.buf+=e},end:function(e){this.buf+=e},read:function(){return this.buf}}}function Ie(e,t){let n=this[e];return n instanceof Date?`__raycast_cached_date__${n.toISOString()}`:Buffer.isBuffer(n)?`__raycast_cached_buffer__${n.toString("base64")}`:t}function Ue(e,t){return typeof t=="string"&&t.startsWith("__raycast_cached_date__")?new Date(t.replace("__raycast_cached_date__","")):typeof t=="string"&&t.startsWith("__raycast_cached_buffer__")?Buffer.from(t.replace("__raycast_cached_buffer__",""),"base64"):t}function H(e){let t=ae.default.createHash("sha1");return ie(t).dispatch(e),t.digest("hex")}var De=Symbol("cache without namespace"),ne=new Map;function Y(e,t,n){let r=n?.cacheNamespace||De,o=ne.get(r)||ne.set(r,new g.Cache({namespace:n?.cacheNamespace})).get(r);if(!o)throw new Error("Missing cache");let l=S(e),s=S(t),a=(0,u.useSyncExternalStore)(o.subscribe,()=>{try{return o.get(l.current)}catch(c){console.error("Could not get Cache data:",c);return}}),i=(0,u.useMemo)(()=>{if(typeof a<"u"){if(a==="undefined")return;try{return JSON.parse(a,Ue)}catch(c){return console.warn("The cached data is corrupted",c),s.current}}else return s.current},[a,s]),d=S(i),p=(0,u.useCallback)(c=>{let $=typeof c=="function"?c(d.current):c;if(typeof $>"u")o.set(l.current,"undefined");else{let v=JSON.stringify($,Ie);o.set(l.current,v)}return $},[o,l,d]);return[i,p]}var V=Symbol();function Oe(e,t,n){let{initialData:r,keepPreviousData:o,internal_cacheKeySuffix:l,...s}=n||{},a=(0,u.useRef)(null),[i,d]=Y(H(t||[])+l,V,{cacheNamespace:H(e)}),p=(0,u.useRef)(i!==V?i:r),c=(0,u.useRef)(void 0),{mutate:$,revalidate:v,...k}=Re(e,t||[],{...s,onData(x,y){c.current=y,s.onData&&s.onData(x,y),!(y&&y.page>0)&&(a.current="promise",p.current=x,d(x))}}),f,w=k.pagination;c.current&&c.current.page>0&&k.data?f=k.data:a.current==="promise"?f=p.current:o&&i!==V?(f=i,w&&(w.hasMore=!0,w.pageSize=i.length)):o&&i===V?f=p.current:i!==V?(f=i,w&&(w.hasMore=!0,w.pageSize=i.length)):f=r;let A=S(f),P=(0,u.useCallback)(async(x,y)=>{let _;try{if(y?.optimisticUpdate){typeof y?.rollbackOnError!="function"&&y?.rollbackOnError!==!1&&(_=structuredClone(A.current));let R=y.optimisticUpdate(A.current);a.current="cache",p.current=R,d(R)}return await $(x,{shouldRevalidateAfter:y?.shouldRevalidateAfter})}catch(R){if(typeof y?.rollbackOnError=="function"){let T=y.rollbackOnError(A.current);a.current="cache",p.current=T,d(T)}else y?.optimisticUpdate&&y?.rollbackOnError!==!1&&(a.current="cache",p.current=_,d(_));throw R}},[d,$,A,p,a]);return(0,u.useEffect)(()=>{i!==V&&(a.current="cache",p.current=i)},[i]),{data:f,isLoading:k.isLoading,error:k.error,mutate:c.current&&c.current.page>0?$:P,pagination:w,revalidate:v}}function Le(e){if(e){let t=Ve(e);if(!t)return!1;if(t.subtype==="json"||t.suffix==="json"||t.suffix&&/\bjson\b/i.test(t.suffix)||t.subtype&&/\bjson\b/i.test(t.subtype))return!0}return!1}var Me=/^([A-Za-z0-9][A-Za-z0-9!#$&^_-]{0,126})\/([A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126});?$/;function Ve(e){let t=e.indexOf(";"),n=t!==-1?e.slice(0,t).trim():e.trim(),r=Me.exec(n.toLowerCase().toLowerCase());if(!r)return;let o=r[1],l=r[2],s,a=l.lastIndexOf("+");return a!==-1&&(s=l.substring(a+1),l=l.substring(0,a)),{type:o,subtype:l,suffix:s}}async function We(e){if(!e.ok)throw new Error(e.statusText);let t=e.headers.get("content-type");return t&&Le(t)?await e.json():await e.text()}function ze(e){return{data:e,hasMore:!1}}function q(e,t){let{parseResponse:n,mapResult:r,initialData:o,execute:l,keepPreviousData:s,onError:a,onData:i,onWillExecute:d,failureToastOptions:p,...c}=t||{},$={initialData:o,execute:l,keepPreviousData:s,onError:a,onData:i,onWillExecute:d,failureToastOptions:p},v=S(n||We),k=S(r||ze),f=(0,u.useRef)(null),w=(0,u.useRef)(null),A=typeof e=="function"?e({page:0}):void 0;(!f.current||typeof w.current>"u"||w.current!==A)&&(f.current=e),w.current=A;let P=(0,u.useRef)(null),x=(0,u.useCallback)((R,T)=>async W=>{let z=await fetch(R(W),{signal:P.current?.signal,...T}),F=await v.current(z);return k.current?.(F)},[v,k]),y=(0,u.useCallback)(async(R,T)=>{let W=await fetch(R,{signal:P.current?.signal,...T}),z=await v.current(W);return k.current(z)?.data},[v,k]),_=(0,u.useMemo)(()=>w.current?x:y,[w,y,x]);return Oe(_,[f.current,c],{...$,internal_cacheKeySuffix:w.current+H(k.current)+H(v.current),abortable:P})}var fe=require("react");var oe="https://kite.kagi.com/kite.json",ce="https://news.kagi.com";function le(e){try{return new URL(e).hostname.replace("www.","")}catch{return e}}function N(e){return e.replace(/<[^>]*>/g,"")}function ue(e){return e.map(t=>{let r=(t.articles?.map(o=>({name:o.title.length>50?o.title.substring(0,50)+"...":o.title,url:o.link}))||[]).filter((o,l,s)=>l===s.findIndex(a=>a.url===o.url));return{id:`cluster-${t.cluster_number}`,title:t.title,summary:t.short_summary,sources:r,uniqueDomains:t.unique_domains,numberOfTitles:t.number_of_titles,businessAnglePoints:t.business_angle_points||[],businessAngleText:t.business_angle_text,category:t.category,culinarSignificance:t.culinary_significance,designPrinciples:t.design_principles,destinationHighlights:t.destination_highlights,didYouKnow:t.did_you_know,diyTips:t.diy_tips,economicImplications:t.economic_implications,emoji:t.emoji,futureOutlook:t.future_outlook,gameplayMechanics:t.gameplay_mechanics||[],geopoliticalContext:t.geopolitical_context,highlights:t.talking_points||[],historicalBackground:t.historical_background,humanitarianImpact:t.humanitarian_impact,industryImpact:t.industry_impact||[],internationalReactions:t.international_reactions||[],keyPlayers:t.key_players||[],leagueStandings:t.league_standings,location:t.location,performanceStatistics:t.performance_statistics||[],perspectives:t.perspectives,primary_image:t.primary_image,quote:t.quote,quoteAttribution:t.quote_attribution,quoteAuthor:t.quote_author,quoteSourceUrl:t.quote_source_url,scientificSignificance:t.scientific_significance||[],secondary_image:t.secondary_image,suggestedQna:t.suggested_qna||[],technicalDetails:t.technical_details||[],technicalSpecifications:t.technical_specifications,timeline:t.timeline,travelAdvisory:t.travel_advisory||[],userActionItems:t.user_action_items||[],userExperienceImpact:t.user_experience_impact}})}function de(e,t){let n=t==="default"?"":`_${t}`,r=e.replace(".json",`${n}.json`),o=`${ce}/${r}`,{isLoading:l,data:s,error:a}=q(o,{parseResponse:async c=>{if(!c.ok)throw new Error(`Failed to fetch: ${c.status}`);return await c.json()}}),i=e==="onthisday.json",{articles:d,events:p}=(0,fe.useMemo)(()=>{if(!s)return{articles:[],events:[]};if(i){let $=s.events||[],v=$.filter(f=>f.type==="event").sort((f,w)=>f.sort_year-w.sort_year),k=$.filter(f=>f.type==="people").sort((f,w)=>f.sort_year-w.sort_year);return{articles:[],events:[...v,...k]}}else return{articles:ue(s.clusters||[]),events:[]}},[s,i]);return{articles:d,events:p,isLoading:l,error:a?a.message:null,isOnThisDay:i}}var he=require("react");function pe(){let{isLoading:e,data:t,error:n}=q(oe,{parseResponse:async o=>{if(!o.ok)throw new Error("Failed to load categories");return await o.json()}});return{categories:(0,he.useMemo)(()=>t?.categories||[],[t]),isLoading:e,error:n}}var I=require("@raycast/api");var O=require("react/jsx-runtime");function me({article:e}){let t=(0,I.getPreferenceValues)(),n=e.sources||[],r=e.highlights||[],o=new Map;n.forEach(a=>{let i=le(a.url)||"unknown";o.has(i)||o.set(i,[]),o.get(i).push(a)});let l=Array.from(o.keys()).sort(),s=`# ${e.title}`;if(t.showPrimaryImage&&e.primary_image){let a=e.primary_image;a.url&&(s+=`

![Primary Image](${a.url})`,a.caption&&(s+=`

*${a.caption}*`))}if(s+=`

## Summary
${e.summary||""}`,t.showTalkingPoints&&r.length>0&&(s+=`

## Highlights
`,r.forEach(a=>{s+=`- ${a}
`})),t.showQuote&&e.quote&&(s+=`

## Quote
> "${e.quote}"`,e.quoteAuthor&&(s+=`

\u2014 ${e.quoteAuthor}`,e.quoteAttribution&&(s+=` (${e.quoteAttribution})`))),t.showSecondaryImage&&e.secondary_image){let a=e.secondary_image;a.url&&(s+=`

![Secondary Image](${a.url})`,a.caption&&(s+=`

*${a.caption}*`))}if(t.showPerspectives&&e.perspectives){let a=e.perspectives;Array.isArray(a)&&a.length>0&&(s+=`

## Perspectives
`,a.forEach(i=>{s+=`- ${i.text}
`}))}if(t.showHistoricalBackground&&e.historicalBackground&&(s+=`

## Historical Background
${e.historicalBackground}`),t.showHumanitarianImpact&&e.humanitarianImpact&&(s+=`

## Humanitarian Impact
${e.humanitarianImpact}`),t.showTechnicalDetails&&e.technicalDetails){let a=e.technicalDetails;Array.isArray(a)&&a.length>0&&(s+=`

## Technical Details
`,a.forEach(i=>{s+=`- ${i}
`}))}if(t.showBusinessAngleText&&e.businessAngleText&&(s+=`

## Business Angle
${e.businessAngleText}`),t.showBusinessAnglePoints&&e.businessAnglePoints){let a=e.businessAnglePoints;Array.isArray(a)&&a.length>0&&(s+=`

## Business Angle Points
`,a.forEach(i=>{s+=`- ${i}
`}))}if(t.showScientificSignificance&&e.scientificSignificance){let a=e.scientificSignificance;Array.isArray(a)&&a.length>0&&(s+=`

## Scientific Significance
`,a.forEach(i=>{s+=`- ${i}
`}))}if(t.showTravelAdvisory&&e.travelAdvisory){let a=e.travelAdvisory;Array.isArray(a)&&a.length>0&&(s+=`

## Travel Advisory
`,a.forEach(i=>{s+=`- ${i}
`}))}if(t.showPerformanceStatistics&&e.performanceStatistics){let a=e.performanceStatistics;Array.isArray(a)&&a.length>0&&(s+=`

## Performance Statistics
`,a.forEach(i=>{s+=`- ${i}
`}))}if(t.showLeagueStandings&&e.leagueStandings&&(s+=`

## League Standings
${e.leagueStandings}`),t.showDesignPrinciples&&e.designPrinciples&&(s+=`

## Design Principles
${e.designPrinciples}`),t.showUserExperienceImpact&&e.userExperienceImpact&&(s+=`

## Experience Impact
${e.userExperienceImpact}`),t.showGameplayMechanics&&e.gameplayMechanics){let a=e.gameplayMechanics;Array.isArray(a)&&a.length>0&&(s+=`

## Gameplay Mechanics
`,a.forEach(i=>{s+=`- ${i}
`}))}if(t.showIndustryImpact&&e.industryImpact){let a=e.industryImpact;Array.isArray(a)&&a.length>0&&(s+=`

## Industry Impact
`,a.forEach(i=>{s+=`- ${i}
`}))}if(t.showTechnicalSpecifications&&e.technicalSpecifications&&(s+=`

## Technical Specifications
${e.technicalSpecifications}`),t.showTimeline&&e.timeline){let a=e.timeline;Array.isArray(a)&&a.length>0&&(s+=`

## Timeline
`,a.forEach(i=>{s+=`- **${i.date}**: ${i.content}
`}))}if(t.showInternationalReactions&&e.internationalReactions){let a=e.internationalReactions;Array.isArray(a)&&a.length>0&&(s+=`

## International Reactions
`,a.forEach(i=>{s+=`- ${i}
`}))}if(t.showSuggestedQna&&e.suggestedQna){let a=e.suggestedQna;Array.isArray(a)&&a.length>0&&(s+=`

## Quick Questions
`,a.forEach(i=>{s+=`**${i.question}**

${i.answer}

`}))}if(t.showUserActionItems&&e.userActionItems){let a=e.userActionItems;Array.isArray(a)&&a.length>0&&(s+=`

## Action Items
`,a.forEach(i=>{s+=`- ${i}
`}))}if(t.showDidYouKnow&&e.didYouKnow&&(s+=`

## Did You Know?
${e.didYouKnow}`),t.showCulinarySignificance&&e.culinarSignificance&&(s+=`

## Culinary Significance
${e.culinarSignificance}`),t.showDestinationHighlights&&e.destinationHighlights&&(s+=`

## Destination Highlights
${e.destinationHighlights}`),t.showDiyTips&&e.diyTips&&(s+=`

## DIY Tips
${e.diyTips}`),t.showEconomicImplications&&e.economicImplications&&(s+=`

## Economic Implications
${e.economicImplications}`),t.showFutureOutlook&&e.futureOutlook&&(s+=`

## Future Outlook
${e.futureOutlook}`),t.showGeopoliticalContext&&e.geopoliticalContext&&(s+=`

## Geopolitical Context
${e.geopoliticalContext}`),t.showKeyPlayers&&e.keyPlayers){let a=e.keyPlayers;Array.isArray(a)&&a.length>0&&(s+=`

## Key Players
`,a.forEach(i=>{s+=`- ${i}
`}))}return t.showLocation&&e.location&&(s+=`

## Location
${e.location}`),(0,O.jsx)(I.Detail,{markdown:s,metadata:n.length>0?(0,O.jsxs)(I.Detail.Metadata,{children:[(0,O.jsx)(I.Detail.Metadata.Label,{title:"Sources",text:`${e.uniqueDomains||0} publishers \u2022 ${e.numberOfTitles||0} articles`}),(0,O.jsx)(I.Detail.Metadata.Separator,{}),l.flatMap(a=>o.get(a).map((d,p)=>{let c=`${a}#${p+1}`,$=d.name&&d.name.trim().length>0?d.name:void 0;return(0,O.jsx)(I.Detail.Metadata.Link,{title:c,target:d.url,text:$||""},d.url)}))]}):void 0})}var J=require("@raycast/api");var Z=require("react/jsx-runtime");function Q({event:e}){let t=`# ${e.year}

${N(e.content)}`;return(0,Z.jsx)(J.Detail,{markdown:t,metadata:(0,Z.jsx)(J.Detail.Metadata,{children:(0,Z.jsx)(J.Detail.Metadata.Label,{title:"Type",text:e.type})})})}var b=require("react/jsx-runtime");function ge(){let e=(0,h.getPreferenceValues)(),[t,n]=Y("selected-category","world.json"),{categories:r,isLoading:o,error:l}=pe(),{articles:s,events:a,isLoading:i,error:d,isOnThisDay:p}=de(t,e.language);return(0,b.jsx)(h.List,{isLoading:o||i,searchBarAccessory:(0,b.jsx)(h.List.Dropdown,{tooltip:"Select Category",value:t,onChange:c=>n(c),children:r.map(c=>(0,b.jsx)(h.List.Dropdown.Item,{title:c.name,value:c.file},c.file))}),children:l?(0,b.jsx)(h.List.EmptyView,{icon:h.Icon.ExclamationMark,title:"Failed to Load Categories",description:l instanceof Error?l.message:String(l)}):d?(0,b.jsx)(h.List.EmptyView,{icon:h.Icon.ExclamationMark,title:"Failed to Load Content",description:d}):p?a.length===0&&!i?(0,b.jsx)(h.List.EmptyView,{icon:h.Icon.Calendar,title:"No Events Found"}):(0,b.jsxs)(b.Fragment,{children:[(0,b.jsx)(h.List.Section,{title:"Events",children:a.filter(c=>c.type==="event").map((c,$)=>(0,b.jsx)(h.List.Item,{icon:"\u{1F4C5}",title:`${c.year} - ${N(c.content).substring(0,80)}...`,actions:(0,b.jsx)(h.ActionPanel,{children:(0,b.jsx)(h.Action.Push,{title:"View Event",icon:h.Icon.Eye,target:(0,b.jsx)(Q,{event:c})})})},$))}),(0,b.jsx)(h.List.Section,{title:"People",children:a.filter(c=>c.type==="people").map((c,$)=>(0,b.jsx)(h.List.Item,{icon:"\u{1F464}",title:`${c.year} - ${N(c.content).substring(0,80)}...`,actions:(0,b.jsx)(h.ActionPanel,{children:(0,b.jsx)(h.Action.Push,{title:"View Event",icon:h.Icon.Eye,target:(0,b.jsx)(Q,{event:c})})})},$))})]}):s.length===0&&!i?(0,b.jsx)(h.List.EmptyView,{icon:h.Icon.Document,title:"No Articles Found"}):s.map(c=>(0,b.jsx)(h.List.Item,{icon:c.emoji||"\u{1F4F0}",title:c.title,accessories:[{tag:c.category}],actions:(0,b.jsx)(h.ActionPanel,{children:(0,b.jsx)(h.Action.Push,{title:"View Article",icon:h.Icon.Eye,target:(0,b.jsx)(me,{article:c})})})},c.id))})}
