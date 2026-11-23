import en from "../messages/en.json";
import ur from "../messages/ur.json";
export function accountCopy(isUrdu:boolean){return isUrdu?ur.account:en.account;}
export function accountInitials(name:string){return name.trim().split(/\s+/u).filter(Boolean).slice(0,2).map(word=>Array.from(word)[0]).join("").toLocaleUpperCase()||"SR";}

