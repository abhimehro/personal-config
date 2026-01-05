"use strict";var l=Object.defineProperty;var u=Object.getOwnPropertyDescriptor;var m=Object.getOwnPropertyNames;var p=Object.prototype.hasOwnProperty;var h=(e,r)=>{for(var o in r)l(e,o,{get:r[o],enumerable:!0})},g=(e,r,o,n)=>{if(r&&typeof r=="object"||typeof r=="function")for(let i of m(r))!p.call(e,i)&&i!==o&&l(e,i,{get:()=>r[i],enumerable:!(n=u(r,i))||n.enumerable});return e};var y=e=>g(l({},"__esModule",{value:!0}),e);var w={};h(w,{default:()=>d});module.exports=y(w);var t=require("@raycast/api");var c=require("child_process");function a(e){return(0,c.execSync)(`
      if [ -f "${e}" ]; then
        echo true
      else
        echo false
      fi
    `,{encoding:"utf-8"}).replace(/\n/g,"")==="true"}function f(e){(0,c.execSync)(`/usr/sbin/dot_clean "${e}"`)}async function d(){try{let o=(await(0,t.getSelectedFinderItems)()).map(s=>s.path).filter(s=>!a(s));if(!o.length){await(0,t.showHUD)("No folders selected");return}let i={title:"Are you sure you want to delete ._ files in the following directories?",message:o.map(s=>s.length===1?`"${s}"`:`"${s.split("/").at(-2)}"`).join(", "),icon:{source:t.Icon.Trash,tintColor:t.Color.Red},primaryAction:{title:"Delete",style:t.Alert.ActionStyle.Destructive}};await(0,t.confirmAlert)(i)&&(o.forEach(f),await(0,t.showHUD)("._ files deleted"))}catch(e){console.error(e),await(0,t.showHUD)("No folders selected")}}
