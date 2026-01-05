"use strict";var q=Object.create;var w=Object.defineProperty;var G=Object.getOwnPropertyDescriptor;var J=Object.getOwnPropertyNames;var Q=Object.getPrototypeOf,Y=Object.prototype.hasOwnProperty;var b=(o,e)=>()=>(e||o((e={exports:{}}).exports,e),e.exports),Z=(o,e)=>{for(var n in e)w(o,n,{get:e[n],enumerable:!0})},k=(o,e,n,t)=>{if(e&&typeof e=="object"||typeof e=="function")for(let i of J(e))!Y.call(o,i)&&i!==n&&w(o,i,{get:()=>e[i],enumerable:!(t=G(e,i))||t.enumerable});return o};var u=(o,e,n)=>(n=o!=null?q(Q(o)):{},k(e||!o||!o.__esModule?w(n,"default",{value:o,enumerable:!0}):n,o)),_=o=>k(w({},"__esModule",{value:!0}),o);var D=b((ce,x)=>{"use strict";function ee(o){var e=void 0;typeof o=="string"?e=[o]:e=o.raw;for(var n="",t=0;t<e.length;t++)n+=e[t].replace(/\\\n[ \t]*/g,"").replace(/\\`/g,"`"),t<(arguments.length<=1?0:arguments.length-1)&&(n+=arguments.length<=t+1?void 0:arguments[t+1]);var i=n.split(`
`),r=null;return i.forEach(function(s){var d=s.match(/^(\s+)\S+/);if(d){var y=d[1].length;r?r=Math.min(r,y):r=y}}),r!==null&&(n=i.map(function(s){return s[0]===" "?s.slice(r):s}).join(`
`)),n=n.trim(),n.replace(/\\n/g,`
`)}typeof x<"u"&&(x.exports=ee)});var O=b((ye,L)=>{"use strict";var te=require("os"),I=te.homedir();L.exports=o=>{if(typeof o!="string")throw new TypeError(`Expected a string, got ${typeof o}`);return I?o.replace(/^~(?=$|\/|\\)/,I):o}});var ie={};Z(ie,{default:()=>ne});module.exports=_(ie);var a=require("@raycast/api");var S=(t=>(t.iOS="ios",t.macOS="macos",t.tvOS="tvos",t))(S||{});var V=require("child_process"),A=require("util"),h=(0,A.promisify)(V.exec);var j=u(D());var g=(t=>(t.Empty="Empty",t.SwiftUI="SwiftUI",t.UIKit="UIKit",t))(g||{});var c=u(require("fs")),v=o=>c.default.promises.access(o,c.default.constants.F_OK).then(()=>!0).catch(()=>!1),me=c.default.promises.readdir,F=c.default.promises.mkdir,E=c.default.promises.rm,de=c.default.promises.readFile,U=c.default.promises.writeFile,fe=c.default.promises.rm;var R=u(O()),P=u(require("path"));var $=require("@raycast/api"),re=(0,$.getPreferenceValues)();var X=re;var f=class o{static{this.scaffoldTemplateFiles=[{path:"playground.xcworkspace",name:"contents",extension:"xcworkspacedata",contents:`
      <?xml version="1.0" encoding="UTF-8"?>
      <Workspace version="1.0">
        <FileRef location="group:">
        </FileRef>
      </Workspace>
      `}]}static get defaultSwiftPlaygroundLocation(){return X.playgroundDefaultLocation}static async createSwiftPlayground(e,n){let t=await o.makeSwiftPlaygroundPath(e.location,e.name,n);if(!n&&await v(t))return{name:e.name,path:t,alreadyExists:!0,open:()=>h(`open ${t}`).then()};await F(t);let i=[...o.scaffoldTemplateFiles,o.swiftSourceContentsTemplateFile(e.template),o.contentsTemplateFile(e.platform,e.swiftVersion)];try{await Promise.all(i.map(async r=>{let s=t;r.path&&(s=P.join(s,r.path),await F(s)),s=P.join(s,[r.name,r.extension].join(".")),await U(s,(0,j.default)(r.contents))}))}catch(r){try{await E(t,{recursive:!0})}catch(s){console.error(s)}throw r}return{name:e.name,path:t,alreadyExists:!1,open:()=>h(`open ${t}`).then()}}static async makeSwiftPlaygroundPath(e,n,t){let i="",r=null,s=(0,R.default)(e);do{let d=new Date().toLocaleDateString().replaceAll("/","-").replaceAll(".","-"),y=r==null?`${n}-${d}.playground`:`${n}-${d}-${r}.playground`;i=P.join(s,y),r=r==null?1:r+1}while(await v(i)&&t);return i}static contentsTemplateFile(e,n){return{name:"contents",extension:"xcplayground",contents:`
      <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
      <playground version='7.0' 
                  target-platform='${e.toLowerCase()}' 
                  swift-version='${n}'
                  buildActiveScheme='true' 
                  executeOnSourceChanges='false' 
                  importAppTypes='true'>
      </playground>
      `}}static swiftSourceContentsTemplateFile(e){let n;switch(e){case"Empty":n=`import Foundation

`;break;case"SwiftUI":n=`
        import PlaygroundSupport
        import SwiftUI
        
        struct ContentView: View {
        
            var body: some View {
                Text("Hello World")
            }
            
        }
        
        PlaygroundPage.current.liveView = UIHostingController(rootView: ContentView())
        `;break;case"UIKit":n=`
        import Foundation
        import PlaygroundSupport
        import UIKit

        class ViewController : UIViewController {
          override func viewDidLoad() {
            super.viewDidLoad()
          }
        }

        let viewController = ViewController()
        viewController.view.frame = CGRect(x: 0, y: 0, width: 300, height: 600)
        PlaygroundPage.current.liveView = viewController
        PlaygroundPage.current.needsIndefiniteExecution = true
        `;break}return{name:"Contents",extension:"swift",contents:n}}};var m=require("@raycast/api");async function K(o,e,n,t){let i=await(0,m.showToast)({style:m.Toast.Style.Animated,title:o});try{let r=await t();return i.style=m.Toast.Style.Success,i.title=e,{isSuccess:!0,result:r,toast:i}}catch(r){return console.error(r),i.style=m.Toast.Style.Failure,i.title=n,i.message=`${r}`,{isSuccess:!1,toast:i}}}var p=u(require("node:path"),1),N=u(require("node:os"),1),M=N.default.homedir();function C(o){let e=p.default.normalize(o)+p.default.sep;return(e.startsWith(M)?e.replace(M+p.default.sep,`~${p.default.sep}`):e).slice(0,-1)}var T=require("react");var W=["5","6"];var l=require("react/jsx-runtime");function H(){let o=(0,a.useNavigation)(),[e,n]=(0,T.useState)(),[t,i]=(0,T.useState)();return(0,l.jsxs)(a.Form,{actions:(0,l.jsxs)(a.ActionPanel,{children:[(0,l.jsx)(a.Action.SubmitForm,{title:"Open or create Swift Playground",onSubmit:r=>B(r,o,!1)}),(0,l.jsx)(a.Action.SubmitForm,{title:"Create Swift Playground",onSubmit:r=>B(r,o,!0)})]}),children:[(0,l.jsx)(a.Form.TextField,{id:"name",title:"Name",defaultValue:"MyPlayground",error:e,onChange:()=>{e&&e.length>0&&n(void 0)},onBlur:r=>{r.target.value?.length==0?n("Please enter a name."):e&&e.length>0&&n(void 0)}}),(0,l.jsx)(a.Form.TextField,{id:"location",title:"Location",defaultValue:f.defaultSwiftPlaygroundLocation,error:t,onChange:()=>{t&&t.length>0&&i(void 0)},onBlur:r=>{r.target.value?.length==0?i("Please enter a location."):t&&t.length>0&&i(void 0)}}),(0,l.jsx)(a.Form.Dropdown,{id:"platform",title:"Platform",defaultValue:"ios",children:Object.keys(S).map(r=>r.toLocaleLowerCase()).map(r=>(0,l.jsx)(a.Form.Dropdown.Item,{value:r,title:r.replace("os","OS")},r))}),(0,l.jsx)(a.Form.Dropdown,{id:"swiftVersion",title:"Swift Version",defaultValue:"6",children:W.map(r=>(0,l.jsx)(a.Form.Dropdown.Item,{value:r,title:r},r))}),(0,l.jsx)(a.Form.Dropdown,{id:"template",title:"Template",defaultValue:"Empty",children:Object.keys(g).map(r=>(0,l.jsx)(a.Form.Dropdown.Item,{value:r,title:r},r))}),(0,l.jsx)(a.Form.Checkbox,{id:"open",label:"Open in Xcode after creation",defaultValue:!0})]})}async function B(o,e,n){if(!o.name||!o.location)return;let t=await K("Creating Swift Playground","Swift Playground successfully created","An error occurred while trying to create the Swift Playground",async()=>await f.createSwiftPlayground(o,n));if(!t.result)return;if(t.result.alreadyExists&&!o.open){t.toast.style=a.Toast.Style.Failure,t.toast.title="Swift Playground already exists";return}let i=["Swift Playground",t.result.alreadyExists?"opened":"created","at",C(t.result.path)].join(" ");if(o.open)try{await t.result.open(),await(0,a.showHUD)(i)}catch{t.toast.style=a.Toast.Style.Failure,t.toast.title="Swift Playground could not be opened"}else t.toast.title=i;e.pop()}var z=require("react/jsx-runtime"),ne=()=>(0,z.jsx)(H,{});
