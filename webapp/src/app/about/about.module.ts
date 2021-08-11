import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { AboutRoutingModule } from './about-routing.module';
import { SharedModule } from '../shared/shared.module';
import { AboutComponent } from './about.component';
import { InfoListComponent } from './info-list/info-list.component';
import { AppInfoResolver } from './shared/services/app-info.resolver';

@NgModule({
  declarations: [
    AboutComponent,
    InfoListComponent,
  ],
  imports: [
    CommonModule,
    AboutRoutingModule,

    SharedModule,
  ],
  providers: [
    AppInfoResolver,
  ]
})
export class AboutModule { }
