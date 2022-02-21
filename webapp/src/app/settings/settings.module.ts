import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ReactiveFormsModule } from '@angular/forms';

import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzPageHeaderModule } from 'ng-zorro-antd/page-header';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzSwitchModule } from 'ng-zorro-antd/switch';
import { NzCheckboxModule } from 'ng-zorro-antd/checkbox';
import { NzRadioModule } from 'ng-zorro-antd/radio';
import { NzSliderModule } from 'ng-zorro-antd/slider';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzListModule } from 'ng-zorro-antd/list';
import { NzDropDownModule } from 'ng-zorro-antd/dropdown';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzDividerModule } from 'ng-zorro-antd/divider';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzCollapseModule } from 'ng-zorro-antd/collapse';

import { SharedModule } from '../shared/shared.module';
import { SettingsResolver } from './shared/services/settings.resolver';
import { EmailNotificationSettingsResolver } from './shared/services/email-notification-settings.resolver';
import { ServerchanNotificationSettingsResolver } from './shared/services/serverchan-notification-settings.resolver';
import { PushplusNotificationSettingsResolver } from './shared/services/pushplus-notification-settings.resolver';
import { WebhookSettingsResolver } from './shared/services/webhook-settings.resolver';
import { SettingsRoutingModule } from './settings-routing.module';
import { SettingsComponent } from './settings.component';
import { SwitchActionableDirective } from './shared/directives/switch-actionable.directive';
import { DiskSpaceSettingsComponent } from './disk-space-settings/disk-space-settings.component';
import { NotificationSettingsComponent } from './notification-settings/notification-settings.component';
import { LoggingSettingsComponent } from './logging-settings/logging-settings.component';
import { DanmakuSettingsComponent } from './danmaku-settings/danmaku-settings.component';
import { PostProcessingSettingsComponent } from './post-processing-settings/post-processing-settings.component';
import { RecorderSettingsComponent } from './recorder-settings/recorder-settings.component';
import { HeaderSettingsComponent } from './header-settings/header-settings.component';
import { UserAgentEditDialogComponent } from './header-settings/user-agent-edit-dialog/user-agent-edit-dialog.component';
import { CookieEditDialogComponent } from './header-settings/cookie-edit-dialog/cookie-edit-dialog.component';
import { OutputSettingsComponent } from './output-settings/output-settings.component';
import { WebhookSettingsComponent } from './webhook-settings/webhook-settings.component';
import { EventSettingsComponent } from './notification-settings/shared/components/event-settings/event-settings.component';
import { EmailNotificationSettingsComponent } from './notification-settings/email-notification-settings/email-notification-settings.component';
import { EmailSettingsComponent } from './notification-settings/email-notification-settings/email-settings/email-settings.component';
import { ServerchanNotificationSettingsComponent } from './notification-settings/serverchan-notification-settings/serverchan-notification-settings.component';
import { ServerchanSettingsComponent } from './notification-settings/serverchan-notification-settings/serverchan-settings/serverchan-settings.component';
import { PushplusNotificationSettingsComponent } from './notification-settings/pushplus-notification-settings/pushplus-notification-settings.component';
import { PushplusSettingsComponent } from './notification-settings/pushplus-notification-settings/pushplus-settings/pushplus-settings.component';
import { NotifierSettingsComponent } from './notification-settings/shared/components/notifier-settings/notifier-settings.component';
import { WebhookManagerComponent } from './webhook-settings/webhook-manager/webhook-manager.component';
import { WebhookEditDialogComponent } from './webhook-settings/webhook-edit-dialog/webhook-edit-dialog.component';
import { WebhookListComponent } from './webhook-settings/webhook-list/webhook-list.component';
import { OutdirEditDialogComponent } from './output-settings/outdir-edit-dialog/outdir-edit-dialog.component';
import { LogdirEditDialogComponent } from './logging-settings/logdir-edit-dialog/logdir-edit-dialog.component';
import { PathTemplateEditDialogComponent } from './output-settings/path-template-edit-dialog/path-template-edit-dialog.component';

@NgModule({
  declarations: [
    SettingsComponent,
    SwitchActionableDirective,
    DiskSpaceSettingsComponent,
    NotificationSettingsComponent,
    LoggingSettingsComponent,
    DanmakuSettingsComponent,
    PostProcessingSettingsComponent,
    RecorderSettingsComponent,
    HeaderSettingsComponent,
    UserAgentEditDialogComponent,
    CookieEditDialogComponent,
    OutputSettingsComponent,
    WebhookSettingsComponent,
    EventSettingsComponent,
    EmailNotificationSettingsComponent,
    EmailSettingsComponent,
    ServerchanNotificationSettingsComponent,
    ServerchanSettingsComponent,
    PushplusNotificationSettingsComponent,
    PushplusSettingsComponent,
    NotifierSettingsComponent,
    WebhookManagerComponent,
    WebhookEditDialogComponent,
    WebhookListComponent,
    OutdirEditDialogComponent,
    LogdirEditDialogComponent,
    PathTemplateEditDialogComponent,
  ],
  imports: [
    CommonModule,
    SettingsRoutingModule,
    FormsModule,
    ReactiveFormsModule,

    NzSpinModule,
    NzPageHeaderModule,
    NzCardModule,
    NzFormModule,
    NzInputModule,
    NzSwitchModule,
    NzCheckboxModule,
    NzRadioModule,
    NzSliderModule,
    NzSelectModule,
    NzModalModule,
    NzButtonModule,
    NzIconModule,
    NzListModule,
    NzDropDownModule,
    NzToolTipModule,
    NzDividerModule,
    NzTableModule,
    NzCollapseModule,

    SharedModule,
  ],
  providers: [
    SettingsResolver,
    EmailNotificationSettingsResolver,
    ServerchanNotificationSettingsResolver,
    PushplusNotificationSettingsResolver,
    WebhookSettingsResolver,
  ],
})
export class SettingsModule {}
