"use strict";var a=Object.defineProperty;var c=Object.getOwnPropertyDescriptor;var p=Object.getOwnPropertyNames;var w=Object.prototype.hasOwnProperty;var f=(r,t)=>{for(var i in t)a(r,i,{get:t[i],enumerable:!0})},u=(r,t,i,n)=>{if(t&&typeof t=="object"||typeof t=="function")for(let o of p(t))!w.call(r,o)&&o!==i&&a(r,o,{get:()=>t[o],enumerable:!(n=c(t,o))||n.enumerable});return r};var m=r=>u(a({},"__esModule",{value:!0}),r);var g={};f(g,{default:()=>F});module.exports=m(g);var e=require("@raycast/api"),d=require("child_process"),h=()=>{let r=`
  if application "Finder" is running and frontmost of application "Finder" then
    tell app "Finder"
      set finderWindow to window 1
      set finderWindowPath to (POSIX path of (target of finderWindow as alias))
      return finderWindowPath
    end tell
  else 
    error "Could not get the selected Finder window"
  end if
 `;return new Promise((t,i)=>{let n=(0,d.exec)(`osascript -e '${r}'`,(o,s,l)=>{(o||l)&&i(Error("Could not get the selected Finder window")),t(s.trim())});n.on("close",()=>{n.kill()})})},F=async()=>{let r=(0,e.getPreferenceValues)(),i=(await(0,e.getApplications)()).find(n=>n.bundleId===r.CursorVariant);if(!i){await(0,e.showToast)({style:e.Toast.Style.Failure,title:"Cursor is not installed",primaryAction:{title:"Install Cursor",onAction:()=>(0,e.open)("https://www.cursor.com/")}});return}try{let n=await(0,e.getSelectedFinderItems)();if(n.length){for(let s of n)await(0,e.open)(s.path,i);return}let o=await h();await(0,e.open)(o,i);return}catch{await(0,e.showToast)({style:e.Toast.Style.Failure,title:"No Finder items or window selected"})}};
