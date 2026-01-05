"use strict";var ge=Object.create;var N=Object.defineProperty;var pe=Object.getOwnPropertyDescriptor;var ve=Object.getOwnPropertyNames;var ye=Object.getPrototypeOf,Se=Object.prototype.hasOwnProperty;var U=(t,e)=>()=>(e||t((e={exports:{}}).exports,e),e.exports),be=(t,e)=>{for(var r in e)N(t,r,{get:e[r],enumerable:!0})},Q=(t,e,r,n)=>{if(e&&typeof e=="object"||typeof e=="function")for(let o of ve(e))!Se.call(t,o)&&o!==r&&N(t,o,{get:()=>e[o],enumerable:!(n=pe(e,o))||n.enumerable});return t};var W=(t,e,r)=>(r=t!=null?ge(ye(t)):{},Q(e||!t||!t.__esModule?N(r,"default",{value:t,enumerable:!0}):r,t)),he=t=>Q(N({},"__esModule",{value:!0}),t);var K=U(V=>{"use strict";var p=require("react");function F(){return(F=Object.assign||function(t){for(var e=1;e<arguments.length;e++){var r=arguments[e];for(var n in r)Object.prototype.hasOwnProperty.call(r,n)&&(t[n]=r[n])}return t}).apply(this,arguments)}typeof Symbol<"u"&&(Symbol.iterator||(Symbol.iterator=Symbol("Symbol.iterator"))),typeof Symbol<"u"&&(Symbol.asyncIterator||(Symbol.asyncIterator=Symbol("Symbol.asyncIterator")));var we=typeof window<"u"&&window.document!==void 0&&window.document.createElement!==void 0?p.useLayoutEffect:p.useEffect,Ce={status:"not-requested",loading:!1,result:void 0,error:void 0},$={status:"loading",loading:!0,result:void 0,error:void 0},Z=function(){},xe={initialState:function(t){return t&&t.executeOnMount?$:Ce},executeOnMount:!0,executeOnUpdate:!0,setLoading:function(t){return $},setResult:function(t,e){return{status:"success",loading:!1,result:t,error:void 0}},setError:function(t,e){return{status:"error",loading:!1,result:void 0,error:t}},onSuccess:Z,onError:Z},z=function(t,e,r){!e&&(e=[]);var n,o=(function(s){return F({},xe,{},s)})(r),l=p.useState(null),f=l[0],d=l[1],u=(function(s){var g=p.useState(function(){return s.initialState(s)}),m=g[0],c=g[1],S=p.useCallback(function(){return c(s.initialState(s))},[c,s]),x=p.useCallback(function(){return c(s.setLoading(m))},[m,c]),A=p.useCallback(function(k){return c(s.setResult(k,m))},[m,c]),H=p.useCallback(function(k){return c(s.setError(k,m))},[m,c]),de=p.useCallback(function(k){return c(F({},m,{},k))},[m,c]);return{value:m,set:c,merge:de,reset:S,setLoading:x,setResult:A,setError:H}})(o),i=(n=p.useRef(!1),p.useEffect(function(){return n.current=!0,function(){n.current=!1}},[]),function(){return n.current}),a=(function(){var s=p.useRef(null);return{set:function(g){return s.current=g},get:function(){return s.current},is:function(g){return s.current===g}}})(),h=function(s){return i()&&a.is(s)},O=(function(s){var g=p.useRef(s);return we(function(){g.current=s}),p.useCallback(function(){return g.current},[g])})(function(){for(var s=arguments.length,g=new Array(s),m=0;m<s;m++)g[m]=arguments[m];var c=(function(){try{return Promise.resolve(t.apply(void 0,g))}catch(S){return Promise.reject(S)}})();return d(g),a.set(c),u.setLoading(),c.then(function(S){h(c)&&u.setResult(S),o.onSuccess(S,{isCurrent:function(){return a.is(c)}})},function(S){h(c)&&u.setError(S),o.onError(S,{isCurrent:function(){return a.is(c)}})}),c}),D=p.useCallback(function(){return O().apply(void 0,arguments)},[O]),q=!i();return p.useEffect(function(){var s=function(){return O().apply(void 0,e)};q&&o.executeOnMount&&s(),!q&&o.executeOnUpdate&&s()},e),F({},u.value,{set:u.set,merge:u.merge,reset:u.reset,execute:D,currentPromise:a.get(),currentParams:f})};function _(t,e,r){return z(t,e,r)}V.useAsync=_,V.useAsyncAbortable=function(t,e,r){var n=p.useRef();return _(function(){for(var o=arguments.length,l=new Array(o),f=0;f<o;f++)l[f]=arguments[f];try{n.current&&n.current.abort();var d=new AbortController;return n.current=d,Promise.resolve((function(u,i){try{var a=Promise.resolve(t.apply(void 0,[d.signal].concat(l)))}catch(h){return i(!0,h)}return a&&a.then?a.then(i.bind(null,!1),i.bind(null,!0)):i(!1,value)})(0,function(u,i){if(n.current===d&&(n.current=void 0),u)throw i;return i}))}catch(u){return Promise.reject(u)}},e,r)},V.useAsyncCallback=function(t,e){return z(t,[],F({},e,{executeOnMount:!1,executeOnUpdate:!1}))}});var re=U(G=>{"use strict";var v=require("react");function R(){return R=Object.assign||function(t){for(var e=1;e<arguments.length;e++){var r=arguments[e];for(var n in r)Object.prototype.hasOwnProperty.call(r,n)&&(t[n]=r[n])}return t},R.apply(this,arguments)}var We=typeof Symbol<"u"?Symbol.iterator||(Symbol.iterator=Symbol("Symbol.iterator")):"@@iterator",$e=typeof Symbol<"u"?Symbol.asyncIterator||(Symbol.asyncIterator=Symbol("Symbol.asyncIterator")):"@@asyncIterator";function Ae(t,e){try{var r=t()}catch(n){return e(!0,n)}return r&&r.then?r.then(e.bind(null,!1),e.bind(null,!0)):e(!1,value)}var Oe=typeof window<"u"&&typeof window.document<"u"&&typeof window.document.createElement<"u"?v.useLayoutEffect:v.useEffect,Ie=function(e){var r=v.useRef(e);return Oe(function(){r.current=e}),v.useCallback(function(){return r.current},[r])},Pe={status:"not-requested",loading:!1,result:void 0,error:void 0},Y={status:"loading",loading:!0,result:void 0,error:void 0},Ee=function(e){return Y},Re=function(e,r){return{status:"success",loading:!1,result:e,error:void 0}},Le=function(e,r){return{status:"error",loading:!1,result:void 0,error:e}},X=function(){},De={initialState:function(e){return e&&e.executeOnMount?Y:Pe},executeOnMount:!0,executeOnUpdate:!0,setLoading:Ee,setResult:Re,setError:Le,onSuccess:X,onError:X},ke=function(e){return R({},De,{},e)},Fe=function(e){var r=v.useState(function(){return e.initialState(e)}),n=r[0],o=r[1],l=v.useCallback(function(){return o(e.initialState(e))},[o,e]),f=v.useCallback(function(){return o(e.setLoading(n))},[n,o]),d=v.useCallback(function(a){return o(e.setResult(a,n))},[n,o]),u=v.useCallback(function(a){return o(e.setError(a,n))},[n,o]),i=v.useCallback(function(a){return o(R({},n,{},a))},[n,o]);return{value:n,set:o,merge:i,reset:l,setLoading:f,setResult:d,setError:u}},Me=function(){var e=v.useRef(!1);return v.useEffect(function(){return e.current=!0,function(){e.current=!1}},[]),function(){return e.current}},Te=function(){var e=v.useRef(null);return{set:function(n){return e.current=n},get:function(){return e.current},is:function(n){return e.current===n}}},ee=function(e,r,n){!r&&(r=[]);var o=ke(n),l=v.useState(null),f=l[0],d=l[1],u=Fe(o),i=Me(),a=Te(),h=function(m){return i()&&a.is(m)},O=function(){for(var m=arguments.length,c=new Array(m),S=0;S<m;S++)c[S]=arguments[S];var x=(function(){try{return Promise.resolve(e.apply(void 0,c))}catch(A){return Promise.reject(A)}})();return d(c),a.set(x),u.setLoading(),x.then(function(A){h(x)&&u.setResult(A),o.onSuccess(A,{isCurrent:function(){return a.is(x)}})},function(A){h(x)&&u.setError(A),o.onError(A,{isCurrent:function(){return a.is(x)}})}),x},D=Ie(O),q=v.useCallback(function(){return D().apply(void 0,arguments)},[D]),s=!i();return v.useEffect(function(){var g=function(){return D().apply(void 0,r)};s&&o.executeOnMount&&g(),!s&&o.executeOnUpdate&&g()},r),R({},u.value,{set:u.set,merge:u.merge,reset:u.reset,execute:q,currentPromise:a.get(),currentParams:f})};function te(t,e,r){return ee(t,e,r)}var qe=function(e,r,n){var o=v.useRef(),l=function(){for(var d=arguments.length,u=new Array(d),i=0;i<d;i++)u[i]=arguments[i];try{o.current&&o.current.abort();var a=new AbortController;return o.current=a,Promise.resolve(Ae(function(){return Promise.resolve(e.apply(void 0,[a.signal].concat(u)))},function(h,O){if(o.current===a&&(o.current=void 0),h)throw O;return O}))}catch(h){return Promise.reject(h)}};return te(l,r,n)},Ne=function(e,r){return ee(e,[],R({},r,{executeOnMount:!1,executeOnUpdate:!1}))};G.useAsync=te;G.useAsyncAbortable=qe;G.useAsyncCallback=Ne});var j=U((_e,J)=>{"use strict";process.env.NODE_ENV==="production"?J.exports=K():J.exports=re()});var je={};be(je,{default:()=>me});module.exports=he(je);var T=require("react"),L=require("@raycast/api");var I=require("react"),y=require("@raycast/api"),oe=W(j()),b=require("react/jsx-runtime"),Ve=({onSubmit:t})=>{let[e,r]=(0,I.useState)(""),[n,o]=(0,I.useState)(),[l,f]=(0,I.useState)("new");(0,oe.useAsync)(async()=>{let u=await y.LocalStorage.getItem("test-string-history");u&&o(JSON.parse(u))},[]),(0,I.useEffect)(()=>{ne[l]?r(ne[l]):r(n?.find(u=>u.id===l)?.value||"")},[l]);let d=(0,I.useCallback)(()=>{y.LocalStorage.removeItem("test-string-history"),o(void 0)},[]);return(0,b.jsxs)(y.Form,{actions:(0,b.jsxs)(y.ActionPanel,{children:[(0,b.jsx)(y.Action.SubmitForm,{title:"Test Regex",onSubmit:t}),(0,b.jsx)(y.Action,{title:"Clear Previous Test Strings",onAction:d,shortcut:{modifiers:["cmd"],key:"backspace"}})]}),children:[(0,b.jsxs)(y.Form.Dropdown,{id:"source",title:"",defaultValue:"new",onChange:f,children:[(0,b.jsx)(y.Form.Dropdown.Item,{value:"new",title:"New Test String"}),(0,b.jsx)(y.Form.Dropdown.Item,{value:"lorem",title:"Lorem Ipsum"}),n&&(0,b.jsx)(y.Form.Dropdown.Section,{title:"Previous Test Strings",children:n.map(u=>(0,b.jsx)(y.Form.Dropdown.Item,{value:u.id,title:u.value},u.id))})]}),(0,b.jsx)(y.Form.TextArea,{id:"text",title:"",placeholder:"Enter your test string",value:e,onChange:r})]})},ne={lorem:"Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla malesuada viverra elit, at placerat metus dictum at. Aliquam pretium, massa nec interdum hendrerit, libero ipsum rutrum nibh, iaculis fringilla magna ante sit amet quam. Donec imperdiet leo risus, et accumsan sem malesuada eu. Nunc suscipit urna magna, sit amet tempus lectus laoreet vitae. Fusce in dolor vitae lacus luctus ullamcorper. Maecenas faucibus fringilla feugiat. Phasellus purus mauris, molestie vel dolor eget, posuere iaculis mauris. Nunc blandit neque ut semper ultrices. Cras tempus mollis pharetra. Quisque euismod orci eget augue lobortis feugiat. Suspendisse at consequat eros."},ue=Ve;var fe=W(j());var M=require("@raycast/api"),E=require("react");var se=require("@raycast/api"),ie=require("react/jsx-runtime"),Ge=()=>(0,ie.jsx)(se.List.Item.Detail,{markdown:He}),He=`
# Regular Expression Cheat Sheet

## Character Classes

\`.\`

any character except newline

\`\\w\\d\\s\`

word, digit, whitespace

\`\\W\\D\\S\`

not word, digit, whitespace

\`[abc]\`

any of a, b, or c

\`[^abc]\`

not a, b, or c

\`[a-g]\`

character between a & g

## Anchors

\`^abc$\`

start / end of the string

\`\\b\\B\`

word, not-word boundary

## Escaped characters

\`\\.\\*\\\\\`

escaped special characters

\`\\t\\n\\r\`

tab, linefeed, carriage return

## Groups & Lookaround

\`(abc)\`

capture group

\`\\1\`

backreference to group #1

\`(?:abc)\`

non-capturing group

\`(?=abc)\`

positive lookahead

\`(?!abc)\`

negative lookahead

## Quantifiers & Alternation

\`a*a+a?\`

0 or more, 1 or more, 0 or 1

\`a{5}a{2,}\`

exactly five, two or more

\`a{1,3}\`

between one & three

\`a+?a{2,}?\`

match as few as possible

\`ab|cd\`

match ab or cd

`,ae=Ge;var C=require("@raycast/api"),w=require("react/jsx-runtime"),Ue=({onOptionsChange:t})=>(0,w.jsxs)(C.List.Dropdown,{tooltip:"Regex Options",defaultValue:"gm",onChange:t,children:[(0,w.jsx)(C.List.Dropdown.Item,{title:"No Modifiers",value:""}),(0,w.jsx)(C.List.Dropdown.Item,{title:"Global (/g)",value:"g"}),(0,w.jsx)(C.List.Dropdown.Item,{title:"Case-Insensitive (/i)",value:"i"}),(0,w.jsx)(C.List.Dropdown.Item,{title:"Multiline (/m)",value:"m"}),(0,w.jsx)(C.List.Dropdown.Item,{title:"Global, Case-Insensitive (/gi)",value:"gi"}),(0,w.jsx)(C.List.Dropdown.Item,{title:"Global, Multiline (/gm)",value:"gm"}),(0,w.jsx)(C.List.Dropdown.Item,{title:"Case-Insensitive, Multiline (/im)",value:"im"}),(0,w.jsx)(C.List.Dropdown.Item,{title:"All Modifiers (/gim)",value:"gim"})]}),ce=Ue;var P=require("react/jsx-runtime"),Je=({testString:t})=>{let[e,r]=(0,E.useState)(""),[n,o]=(0,E.useState)(""),[l,f]=(0,E.useState)("gm"),d=(0,E.useCallback)(u=>{f(u)},[]);return(0,E.useEffect)(()=>{if(e===""){o(t);return}try{let u=t.replace(new RegExp(e,l),i=>`|${i}|`);o(u)}catch(u){console.log("regex error",u)}},[t,e,l]),(0,P.jsxs)(M.List,{isShowingDetail:!0,enableFiltering:!1,searchBarPlaceholder:"([A-Z])\\w+",searchText:e,onSearchTextChange:r,searchBarAccessory:(0,P.jsx)(ce,{onOptionsChange:d}),children:[(0,P.jsx)(M.List.Item,{title:"Preview",subtitle:"",detail:(0,P.jsx)(M.List.Item.Detail,{markdown:n})}),(0,P.jsx)(M.List.Item,{title:"Cheat Sheet",subtitle:"",detail:(0,P.jsx)(ae,{})})]})},le=Je;var B=require("react/jsx-runtime");function me(){let[t,e]=(0,T.useState)(""),[r,n]=(0,T.useState)(),{push:o}=(0,L.useNavigation)();(0,fe.useAsync)(async()=>{if(r==="new"){let f={id:Date.now().toString(),value:t},d=await L.LocalStorage.getItem("test-string-history");if(d){let u=JSON.parse(d),i=[f,...u].slice(0,5);await L.LocalStorage.setItem("test-string-history",JSON.stringify(i))}else await L.LocalStorage.setItem("test-string-history",JSON.stringify([f]))}},[r]);let l=(0,T.useCallback)(f=>{e(f.text),n(f.source),o((0,B.jsx)(le,{testString:f.text}))},[]);return(0,B.jsx)(ue,{onSubmit:l})}
