import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { SettingsResolver } from './shared/services/settings.resolver';
import { EmailNotificationSettingsResolver } from './shared/services/email-notification-settings.resolver';
import { PushplusNotificationSettingsResolver } from './shared/services/pushplus-notification-settings.resolver';
import { ServerchanNotificationSettingsResolver } from './shared/services/serverchan-notification-settings.resolver';
import { WebhookSettingsResolver } from './shared/services/webhook-settings.resolver';
import { SettingsComponent } from './settings.component';
import { EmailNotificationSettingsComponent } from './notification-settings/email-notification-settings/email-notification-settings.component';
import { ServerchanNotificationSettingsComponent } from './notification-settings/serverchan-notification-settings/serverchan-notification-settings.component';
import { PushplusNotificationSettingsComponent } from './notification-settings/pushplus-notification-settings/pushplus-notification-settings.component';
import { WebhookManagerComponent } from './webhook-settings/webhook-manager/webhook-manager.component';

const routes: Routes = [
  {
    path: 'email-notification',
    component: EmailNotificationSettingsComponent,
    resolve: {
      settings: EmailNotificationSettingsResolver,
    },
  },
  {
    path: 'serverchan-notification',
    component: ServerchanNotificationSettingsComponent,
    resolve: {
      settings: ServerchanNotificationSettingsResolver,
    },
  },
  {
    path: 'pushplus-notification',
    component: PushplusNotificationSettingsComponent,
    resolve: {
      settings: PushplusNotificationSettingsResolver,
    },
  },
  {
    path: 'webhooks',
    component: WebhookManagerComponent,
    resolve: {
      settings: WebhookSettingsResolver,
    },
  },
  {
    path: '',
    component: SettingsComponent,
    resolve: {
      settings: SettingsResolver,
    },
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class SettingsRoutingModule {}
