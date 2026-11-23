"use client";
import {useEffect,useRef,type ReactNode} from "react";
export function HomeMenu({label,children}:{label:string;children:ReactNode}){
 const menu=useRef<HTMLDetailsElement>(null);
 useEffect(()=>{
  const header=menu.current?.closest("header"),root=header?.closest<HTMLElement>(".home-page");
  const observer=new ResizeObserver(()=>{if(header&&root)root.style.setProperty("--home-header-height",header.getBoundingClientRect().height+"px");});
  if(header)observer.observe(header);
  function escape(event:KeyboardEvent){if(event.key==="Escape"&&menu.current?.open){menu.current.open=false;menu.current.querySelector("summary")?.focus();}}
  function outside(event:PointerEvent){if(menu.current?.open&&event.target instanceof Node&&!menu.current.contains(event.target))menu.current.open=false;}
  document.addEventListener("keydown",escape);document.addEventListener("pointerdown",outside);
  return()=>{observer.disconnect();document.removeEventListener("keydown",escape);document.removeEventListener("pointerdown",outside);};
 },[]);
 return <details className="mobile-menu" ref={menu} onClick={event=>{if((event.target as Element).closest("a")&&menu.current)menu.current.open=false;}}><summary aria-label={label}><span/><span/><span/></summary><nav aria-label={label}>{children}</nav></details>;
}

