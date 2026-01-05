"use strict";var I=Object.create;var m=Object.defineProperty;var C=Object.getOwnPropertyDescriptor;var U=Object.getOwnPropertyNames;var _=Object.getPrototypeOf,P=Object.prototype.hasOwnProperty;var T=(e,t)=>{for(var n in t)m(e,n,{get:t[n],enumerable:!0})},w=(e,t,n,c)=>{if(t&&typeof t=="object"||typeof t=="function")for(let i of U(t))!P.call(e,i)&&i!==n&&m(e,i,{get:()=>t[i],enumerable:!(c=C(t,i))||c.enumerable});return e};var $=(e,t,n)=>(n=e!=null?I(_(e)):{},w(t||!e||!e.__esModule?m(n,"default",{value:e,enumerable:!0}):n,e)),O=e=>w(m({},"__esModule",{value:!0}),e);var L={};T(L,{default:()=>R});module.exports=O(L);var s=require("@raycast/api"),h=require("react");var k=require("node:child_process");function x(e,t,n=[]){return new Promise((c,i)=>{let u=(0,k.execFile)("swift",["-suppress-warnings","-",...n],{timeout:1e4},(o,r,p)=>{if(o){i(new Error(p||o.message));return}try{c(t(r))}catch(g){i(g)}});u.stdin?.write(e),u.stdin?.end()})}async function v(){return x(`
import Foundation
import CoreServices

func appName(for bundleId: String) -> String {
  guard let urls = LSCopyApplicationURLsForBundleIdentifier(bundleId as CFString, nil)?.takeRetainedValue() as? [URL],
        let url = urls.first,
        let bundle = Bundle(url: url) else {
    return bundleId
  }
  if let displayName = bundle.object(forInfoDictionaryKey: "CFBundleDisplayName") as? String {
    return displayName
  }
  if let name = bundle.object(forInfoDictionaryKey: "CFBundleName") as? String {
    return name
  }
  return url.deletingPathExtension().lastPathComponent
}

let scheme = "http" as CFString
let defaultHandler = LSCopyDefaultHandlerForURLScheme(scheme)?.takeRetainedValue() as String?
let handlers = LSCopyAllHandlersForURLScheme(scheme)?.takeRetainedValue() as? [String] ?? []

let payload: [[String: String]] = handlers.compactMap { bundleId in
  guard let urls = LSCopyApplicationURLsForBundleIdentifier(bundleId as CFString, nil)?.takeRetainedValue() as? [URL],
        let url = urls.first else {
    return [
      "bundleId": bundleId,
      "name": appName(for: bundleId),
    ]
  }
  return [
    "bundleId": bundleId,
    "name": appName(for: bundleId),
    "path": url.path,
  ]
}

let result: [String: Any] = [
  "default": defaultHandler as Any,
  "handlers": payload
]

let json = try! JSONSerialization.data(withJSONObject: result, options: [])
print(String(data: json, encoding: .utf8)!)
`,t=>{let n=JSON.parse(t),c=n.handlers?.filter(Boolean).map(i=>({...i,path:i.path??void 0}))??[];return{defaultBrowser:n.default??null,browsers:c}})}async function S(e){await x(`
import Foundation
import CoreServices

let bundleId = CommandLine.arguments[1]
let scheme = "http" as CFString
let status = LSSetDefaultHandlerForURLScheme(scheme, bundleId as CFString)
if status != noErr {
  fputs("Failed with status: \\(status)\\n", stderr)
  exit(1)
}
`,()=>{},[e])}var f=$(require("react")),a=require("@raycast/api");var d=$(require("node:fs")),b=$(require("node:path"));var A=require("react/jsx-runtime");function y(e,t){let n=e instanceof Error?e.message:String(e);return(0,a.showToast)({style:a.Toast.Style.Failure,title:t?.title??"Something went wrong",message:t?.message??n,primaryAction:t?.primaryAction??E(e),secondaryAction:t?.primaryAction?E(e):void 0})}var E=e=>{let t=!0,n="[Extension Name]...",c="";try{let o=JSON.parse((0,d.readFileSync)((0,b.join)(a.environment.assetsPath,"..","package.json"),"utf8"));n=`[${o.title}]...`,c=`https://raycast.com/${o.owner||o.author}/${o.name}`,(!o.owner||o.access==="public")&&(t=!1)}catch{}let i=a.environment.isDevelopment||t,u=e instanceof Error?e?.stack||e?.message||"":String(e);return{title:i?"Copy Logs":"Report Error",onAction(o){o.hide(),i?a.Clipboard.copy(u):(0,a.open)(`https://github.com/raycast/extensions/issues/new?&labels=extension%2Cbug&template=extension_bug_report.yml&title=${encodeURIComponent(n)}&extension-url=${encodeURI(c)}&description=${encodeURIComponent(`#### Error:
\`\`\`
${u}
\`\`\`
`)}`)}}};var l=require("react/jsx-runtime");function R(){let[e,t]=(0,h.useState)([]),[n,c]=(0,h.useState)(null),[i,u]=(0,h.useState)(!0);(0,h.useEffect)(()=>{(async()=>{try{let r=await v();c(r.defaultBrowser),t(r.browsers.sort((p,g)=>p.name.localeCompare(g.name)))}catch(r){await y(r,{title:"Failed to load browsers"})}finally{u(!1)}})()},[]);let o=async r=>{try{await S(r),await(0,s.popToRoot)({clearSearchBar:!0}),await(0,s.closeMainWindow)();return}catch(p){await y(p,{title:"Failed to set default browser"})}};return(0,l.jsxs)(s.List,{isLoading:i,searchBarPlaceholder:"Search browsers\u2026",children:[n?(0,l.jsx)(s.List.Section,{title:"Default",children:e.filter(r=>r.bundleId===n).map(r=>(0,l.jsx)(s.List.Item,{icon:r.path?{fileIcon:r.path}:s.Icon.CheckCircle,title:r.name,subtitle:r.bundleId,accessories:[{tag:{value:"Default",color:"green"}}]},r.bundleId))}):null,(0,l.jsx)(s.List.Section,{title:"Available Browsers",children:e.filter(r=>r.bundleId!==n).map(r=>(0,l.jsx)(s.List.Item,{icon:r.path?{fileIcon:r.path}:s.Icon.Globe,title:r.name,subtitle:r.bundleId,actions:(0,l.jsx)(s.ActionPanel,{children:(0,l.jsx)(s.Action,{title:"Set as Default",icon:s.Icon.CheckCircle,onAction:()=>o(r.bundleId)})})},r.bundleId))})]})}
