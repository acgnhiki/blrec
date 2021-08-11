import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AboutComponent } from './about.component';
import { AppInfoResolver } from './shared/services/app-info.resolver';

const routes: Routes = [
  {
    path: '',
    component: AboutComponent,
    resolve: {
      appInfo: AppInfoResolver,
    },
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class AboutRoutingModule {}
