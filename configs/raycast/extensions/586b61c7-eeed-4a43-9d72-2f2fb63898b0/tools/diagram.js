"use strict";var y=Object.defineProperty;var k=Object.getOwnPropertyDescriptor;var q=Object.getOwnPropertyNames;var I=Object.prototype.hasOwnProperty;var P=(t,e)=>{for(var i in e)y(t,i,{get:e[i],enumerable:!0})},U=(t,e,i,c)=>{if(e&&typeof e=="object"||typeof e=="function")for(let a of q(e))!I.call(t,a)&&a!==i&&y(t,a,{get:()=>e[a],enumerable:!(c=k(e,a))||c.enumerable});return t};var O=t=>U(y({},"__esModule",{value:!0}),t);var W={};P(W,{default:()=>F});module.exports=O(W);var E=require("@raycast/api");async function F(t){let e=typeof t?.query=="string"?t.query:"",i=await E.AI.ask(`Analyze this request and choose the best diagram type: "${e}"

Choose EXACTLY one type from: FLOWCHART, MINDMAP, SEQUENCE.
Then output ONLY Mermaid for that type:

- FLOWCHART => start with "flowchart TD" or "flowchart LR"
- MINDMAP   => start with "mindmap" then the tree
- SEQUENCE  => start with "sequenceDiagram"

Respond with this exact format and nothing else:
TYPE: [FLOWCHART|MINDMAP|SEQUENCE]
\`\`\`mermaid
<mermaid code here>
\`\`\`
`),c=/TYPE:\s*(FLOWCHART|MINDMAP|SEQUENCE)/i,a=/```mermaid\s*([\s\S]*?)\s*```/i,A=c.exec(i),M=a.exec(i);if(!A||!M)throw new Error("Could not parse diagram type or Mermaid content");let m=A[1].toUpperCase(),p=M[1].trim(),x=p,d=e&&e.length>0?e.slice(0,50):"Diagram",C=o=>{let u=o.split(`
`).map(n=>n.trim()),r=[];for(let n of u){if(/^sequenceDiagram/i.test(n)||/^participant\s+/i.test(n)||n==="")continue;let s=/(\S+)\s*-+>{1,2}\s*(\S+)\s*:\s*(.+)/.exec(n);s&&r.push(`${s[1]} -> ${s[2]}: ${s[3]}`)}return r.join(`
`)},R=o=>{let u=o.split(`
`),r=[],n=!1;for(let s of u){let f=s.replace(/\t/g,"  ");if(!n){/^\s*mindmap\s*$/i.test(f)&&(n=!0);continue}if(!f.trim())continue;let w=/^(\s*)(.+)$/.exec(f);if(!w)continue;let N=Math.floor((w[1]||"").length/2),S=w[2].trim();r.push(`${"  ".repeat(N)}- ${S}`)}return r.length===0?`- ${d}`:r.join(`
`)},h,l;switch(m){case"FLOWCHART":{h="https://whimsical.com/api/ai.chatgpt.render-flowchart",l={mermaid:p,title:d};break}case"MINDMAP":{h="https://whimsical.com/api/ai.chatgpt.render-mindmap",l={markdown:R(p),title:d};break}case"SEQUENCE":{h="https://whimsical.com/api/ai.chatgpt.render-sequence-diagram",l={diagram:C(p),title:d};break}default:throw new Error(`Unknown diagram type: ${m}`)}let g=await fetch(h,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(l)});if(!g.ok)throw new Error(`API request failed: ${g.statusText}`);let{fileURL:T}=await g.json(),D={FLOWCHART:"Flowchart",MINDMAP:"Mindmap",SEQUENCE:"Sequence Diagram"}[m]||"Diagram",$=`Briefly summarize what was created in this ${m.toLowerCase()}: "${e}"

Write a single sentence describing the main content/purpose of the diagram. Keep it concise and informative.

Examples:
- "A flowchart showing the user authentication process with login validation steps."
- "A mindmap exploring digital marketing strategies and their key components."
- "A sequence diagram illustrating the API interaction flow for order processing."

Return only the summary sentence, no additional text.`,L=await E.AI.ask($);return{content:[{type:"text",text:`\u2728 **${D} Generated**

${L}

\u{1F517} **Diagram URL:** ${T}`},{type:"text",text:["## Mermaid preview","","```mermaid",x,"```"].join(`
`)},{type:"resource",resource:{uri:T,text:"Open in Whimsical"}}]}}
