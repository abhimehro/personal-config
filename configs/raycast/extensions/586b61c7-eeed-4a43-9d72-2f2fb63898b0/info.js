"use strict";var r=Object.defineProperty;var m=Object.getOwnPropertyDescriptor;var l=Object.getOwnPropertyNames;var p=Object.prototype.hasOwnProperty;var u=(o,e)=>{for(var t in e)r(o,t,{get:e[t],enumerable:!0})},d=(o,e,t,s)=>{if(e&&typeof e=="object"||typeof e=="function")for(let a of l(e))!p.call(o,a)&&a!==t&&r(o,a,{get:()=>e[a],enumerable:!(s=m(e,a))||s.enumerable});return o};var g=o=>d(r({},"__esModule",{value:!0}),o);var h={};u(h,{default:()=>n});module.exports=g(h);var i=require("@raycast/api"),c=require("react/jsx-runtime");function n(){return(0,c.jsx)(i.Detail,{markdown:`
# \u{1F3A8} Whimsical AI Diagram Generator

Transform your ideas into beautiful visual diagrams using AI! This extension intelligently creates flowcharts, mindmaps, and sequence diagrams from your natural language descriptions.

## \u2728 How It Works

The AI automatically chooses the best diagram type based on your description:

- **\u{1F504} Flowcharts** - For processes, workflows, decision trees, step-by-step procedures
- **\u{1F9E0} Mindmaps** - For brainstorming, organizing ideas, exploring topics and concepts  
- **\u{1F4CA} Sequence Diagrams** - For system interactions, API flows, communication patterns

## \u{1F680} Quick Start Guide

1. **Open Raycast AI Chat** (\u2318 + Space, then type "AI")
2. **Select "Whimsical Diagram" tool** from the available tools
3. **Describe what you want to visualize:**
   - "Create a user onboarding process"
   - "Brainstorm marketing strategies for a new app"
   - "Show the API flow for user authentication"
4. **Get your diagram!** The AI will generate and render it instantly

## \u{1F4A1} Example Prompts

**For Flowcharts:**
- "Design a customer support ticket resolution process"
- "Map out the software deployment workflow"
- "Create a decision tree for choosing a programming language"

**For Mindmaps:**
- "Explore different revenue models for SaaS businesses"
- "Organize project management best practices"
- "Break down the components of effective teamwork"

**For Sequence Diagrams:**
- "Show how a mobile app handles user login"
- "Diagram the checkout process for an e-commerce site"
- "Map the communication flow in a microservices architecture"

## \u{1F3AF} Tips for Best Results

- **Be specific** - Include key steps, components, or participants
- **Use action words** - "process", "flow", "interaction", "strategy"
- **Mention context** - What domain or industry is this for?

**\u2728 No setup required** - Uses Raycast AI and Whimsical's rendering API seamlessly!
  `})}
