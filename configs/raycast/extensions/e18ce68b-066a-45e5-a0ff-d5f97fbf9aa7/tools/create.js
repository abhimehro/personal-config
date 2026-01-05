"use strict";var h=Object.create;var l=Object.defineProperty;var c=Object.getOwnPropertyDescriptor;var p=Object.getOwnPropertyNames;var d=Object.getPrototypeOf,f=Object.prototype.hasOwnProperty;var $=(t,e)=>{for(var n in e)l(t,n,{get:e[n],enumerable:!0})},r=(t,e,n,a)=>{if(e&&typeof e=="object"||typeof e=="function")for(let i of p(e))!f.call(t,i)&&i!==n&&l(t,i,{get:()=>e[i],enumerable:!(a=c(e,i))||a.enumerable});return t};var u=(t,e,n)=>(n=t!=null?h(d(t)):{},r(e||!t||!t.__esModule?l(n,"default",{value:t,enumerable:!0}):n,t)),y=t=>r(l({},"__esModule",{value:!0}),t);var b={};$(b,{confirmation:()=>w,default:()=>g});module.exports=y(b);var s=require("@raycast/api"),o=u(require("fs")),m=t=>`<!DOCTYPE html>

<html lang="en">
	<head>
		<meta charset="UTF-8" />
		<meta name="viewport" content="width=device-width, initial-scale=1.0" />
		<title>${t.title}</title>
    <meta name="description" content="${t.about}">
		<link
			href="https://unpkg.com/tailwindcss@^2/dist/tailwind.min.css"
			rel="stylesheet"
		/>
		<link
			href="https://cdn.jsdelivr.net/npm/daisyui@latest/dist/full.css"
			rel="stylesheet"
		/>
	</head>

	<body>
    ${t.html}

		<script async defer>
			${t.js}
		</script>
	</body>
</html>`;async function g(t){return console.log(t),o.default.writeFileSync(`${s.environment.supportPath}/${t.filename}.html`,m(t)),(0,s.open)(`${s.environment.supportPath}/${t.filename}.html`),`\`${s.environment.supportPath}/${t.filename}.html\` has been created.`}var w=async t=>({message:`Create this app in \`${s.environment.supportPath}/${t.filename}.html\`?
\`\`\`
${m(t)}
\`\`\``});0&&(module.exports={confirmation});
