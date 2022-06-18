import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
} from '@angular/core';
import { ActivatedRoute } from '@angular/router';

import pick from 'lodash-es/pick';

import {
  KEYS_OF_MESSAGE_TEMPLATE_SETTINGS,
  KEYS_OF_NOTIFICATION_SETTINGS,
  KEYS_OF_NOTIFIER_SETTINGS,
  KEYS_OF_PUSHDEER_SETTINGS,
  MessageTemplateSettings,
  NotificationSettings,
  NotifierSettings,
  PushdeerNotificationSettings,
  PushdeerSettings,
} from '../../shared/setting.model';

@Component({
  selector: 'app-pushdeer-notification-settings',
  templateUrl: './pushdeer-notification-settings.component.html',
  styleUrls: ['./pushdeer-notification-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PushdeerNotificationSettingsComponent implements OnInit {
  pushdeerSettings!: PushdeerSettings;
  notifierSettings!: NotifierSettings;
  notificationSettings!: NotificationSettings;
  messageTemplateSettings!: MessageTemplateSettings;

  constructor(
    private changeDetector: ChangeDetectorRef,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    this.route.data.subscribe((data) => {
      const settings = data.settings as PushdeerNotificationSettings;
      this.pushdeerSettings = pick(settings, KEYS_OF_PUSHDEER_SETTINGS);
      this.notifierSettings = pick(settings, KEYS_OF_NOTIFIER_SETTINGS);
      this.notificationSettings = pick(settings, KEYS_OF_NOTIFICATION_SETTINGS);
      this.messageTemplateSettings = pick(
        settings,
        KEYS_OF_MESSAGE_TEMPLATE_SETTINGS
      );
      this.changeDetector.markForCheck();
    });
  }
}
