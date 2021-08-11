"use strict";(self.webpackChunkblrec=self.webpackChunkblrec||[]).push([[659],{9659:(M,c,i)=>{i.r(c),i.d(c,{AboutModule:()=>y});var u=i(8583),p=i(6983),t=i(7716),h=i(4670),l=i(2340),g=i(1841);const Z=l.N.apiUrl;let A=(()=>{class n{constructor(o){this.http=o}getLatestVerisonString(){return this.http.get(Z+"/api/v1/update/version/latest")}}return n.\u0275fac=function(o){return new(o||n)(t.LFG(g.eN))},n.\u0275prov=t.Yz7({token:n,factory:n.\u0275fac,providedIn:"root"}),n})(),m=(()=>{class n{constructor(o){this.latestVesion$=o.getLatestVerisonString()}}return n.\u0275fac=function(o){return new(o||n)(t.Y36(A))},n.\u0275cmp=t.Xpm({type:n,selectors:[["app-info-list"]],inputs:{appInfo:"appInfo"},decls:42,vars:4,consts:[[1,"info-list"],[1,"info-item"],[1,"label"],[1,"desc"],["href","https://github.com/acgnhiki/blrec","target","_blank"],["href","https://github.com/acgnhiki/blrec/issues","target","_blank"],["href","https://choosealicense.com/licenses/gpl-3.0","target","_blank"],["href","mailto:acgnhiki@outlook.com","target","_blank"],["href","https://afdian.net/@acgnhiki","target","_blank"]],template:function(o,a){1&o&&(t.TgZ(0,"ul",0),t.TgZ(1,"li",1),t.TgZ(2,"span",2),t._uU(3,"\u5f53\u524d\u7248\u672c"),t.qZA(),t.TgZ(4,"span",3),t._uU(5),t.qZA(),t.qZA(),t.TgZ(6,"li",1),t.TgZ(7,"span",2),t._uU(8,"\u6700\u65b0\u7248\u672c"),t.qZA(),t.TgZ(9,"span",3),t._uU(10),t.ALo(11,"async"),t.qZA(),t.qZA(),t.TgZ(12,"li",1),t.TgZ(13,"span",2),t._uU(14,"\u9879\u76ee\u4e3b\u9875"),t.qZA(),t.TgZ(15,"span",3),t.TgZ(16,"a",4),t._uU(17,"https://github.com/acgnhiki/blrec"),t.qZA(),t.qZA(),t.qZA(),t.TgZ(18,"li",1),t.TgZ(19,"span",2),t._uU(20,"\u95ee\u9898\u53cd\u9988"),t.qZA(),t.TgZ(21,"span",3),t.TgZ(22,"a",5),t._uU(23,"https://github.com/acgnhiki/blrec/issues"),t.qZA(),t.qZA(),t.qZA(),t.TgZ(24,"li",1),t.TgZ(25,"span",2),t._uU(26,"\u8bb8\u53ef\u534f\u8bae"),t.qZA(),t.TgZ(27,"span",3),t.TgZ(28,"a",6),t._uU(29,"GNU GPLv3"),t.qZA(),t.qZA(),t.qZA(),t.TgZ(30,"li",1),t.TgZ(31,"span",2),t._uU(32,"\u8054\u7cfb\u65b9\u5f0f"),t.qZA(),t.TgZ(33,"span",3),t.TgZ(34,"a",7),t._uU(35,"acgnhiki@outlook.com"),t.qZA(),t.qZA(),t.qZA(),t.TgZ(36,"li",1),t.TgZ(37,"span",2),t._uU(38,"\u6295\u5582\u8d5e\u52a9"),t.qZA(),t.TgZ(39,"span",3),t.TgZ(40,"a",8),t._uU(41,"https://afdian.net/@acgnhiki"),t.qZA(),t.qZA(),t.qZA(),t.qZA()),2&o&&(t.xp6(5),t.Oqu(a.appInfo.version),t.xp6(5),t.Oqu(t.lcZ(11,2,a.latestVesion$)))},pipes:[u.Ov],styles:['@charset "UTF-8";.info-list[_ngcontent-%COMP%]   .info-item[_ngcontent-%COMP%]{display:flex;flex-wrap:wrap;align-items:center;margin:0;padding:1em 2em;border-top:1px solid rgba(0,0,0,.06)}.info-list[_ngcontent-%COMP%]   .info-item[_ngcontent-%COMP%]:first-child{border-top:none}.info-list[_ngcontent-%COMP%]   .info-item[_ngcontent-%COMP%]   .label[_ngcontent-%COMP%]:after{content:"\\ff1a"}.info-list[_ngcontent-%COMP%]{margin:0;padding:0;list-style:none}'],changeDetection:0}),n})(),d=(()=>{class n{constructor(o,a){this.changeDetector=o,this.route=a}ngOnInit(){this.route.data.subscribe(o=>{this.appInfo=o.appInfo,this.changeDetector.markForCheck()})}}return n.\u0275fac=function(o){return new(o||n)(t.Y36(t.sBO),t.Y36(p.gz))},n.\u0275cmp=t.Xpm({type:n,selectors:[["app-about"]],decls:4,vars:1,consts:[[1,"inner-content"],[1,"about-page"],[3,"appInfo"]],template:function(o,a){1&o&&(t.TgZ(0,"div",0),t.TgZ(1,"div",1),t.TgZ(2,"app-page-section"),t._UZ(3,"app-info-list",2),t.qZA(),t.qZA(),t.qZA()),2&o&&(t.xp6(3),t.Q6J("appInfo",a.appInfo))},directives:[h.g,m],styles:[".inner-content[_ngcontent-%COMP%]{height:100%;width:100%;position:relative;display:block;margin:0;padding:1rem;background:#f1f3f4;overflow:auto}.inner-content[_ngcontent-%COMP%]   .about-page[_ngcontent-%COMP%]{max-width:680px;margin:0 auto}"]}),n})();var v=i(5304),T=i(9825),b=i(7158),C=i(3080);const s=l.N.apiUrl;let U=(()=>{class n{constructor(o){this.http=o}getAppInfo(){return this.http.get(s+"/api/v1/app/info")}getAppStatus(){return this.http.get(s+"/api/v1/app/status")}restartApp(){return this.http.post(s+"/api/v1/app/restart",null)}exitApp(){return this.http.post(s+"/api/v1/app/exit",null)}}return n.\u0275fac=function(o){return new(o||n)(t.LFG(g.eN))},n.\u0275prov=t.Yz7({token:n,factory:n.\u0275fac,providedIn:"root"}),n})(),f=(()=>{class n{constructor(o,a,r){this.logger=o,this.notification=a,this.appService=r}resolve(o,a){return this.appService.getAppInfo().pipe((0,T.X)(3,300),(0,v.K)(r=>{throw this.logger.error("Failed to get app info:",r),this.notification.error("\u83b7\u53d6\u540e\u7aef\u5e94\u7528\u4fe1\u606f\u51fa\u9519",r.message,{nzDuration:0}),r}))}}return n.\u0275fac=function(o){return new(o||n)(t.LFG(b.Kf),t.LFG(C.zb),t.LFG(U))},n.\u0275prov=t.Yz7({token:n,factory:n.\u0275fac}),n})();const F=[{path:"",component:d,resolve:{appInfo:f}}];let I=(()=>{class n{}return n.\u0275fac=function(o){return new(o||n)},n.\u0275mod=t.oAB({type:n}),n.\u0275inj=t.cJS({imports:[[p.Bz.forChild(F)],p.Bz]}),n})();var q=i(4466);let y=(()=>{class n{}return n.\u0275fac=function(o){return new(o||n)},n.\u0275mod=t.oAB({type:n}),n.\u0275inj=t.cJS({providers:[f],imports:[[u.ez,I,q.m]]}),n})()}}]);