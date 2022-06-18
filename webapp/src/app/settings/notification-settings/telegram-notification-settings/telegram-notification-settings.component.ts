import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
} from '@angular/core';
import { ActivatedRoute } from '@angular/router';

import pick from 'lodash-es/pick';

import {
  NotificationSettings,
  TelegramSettings,
  NotifierSettings,
  TelegramNotificationSettings,
  KEYS_OF_TELEGRAM_SETTINGS,
  KEYS_OF_NOTIFIER_SETTINGS,
  KEYS_OF_NOTIFICATION_SETTINGS,
  MessageTemplateSettings,
  KEYS_OF_MESSAGE_TEMPLATE_SETTINGS,
} from '../../shared/setting.model';

@Component({
  selector: 'app-telegram-notification-settings',
  templateUrl: './telegram-notification-settings.component.html',
  styleUrls: ['./telegram-notification-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TelegramNotificationSettingsComponent implements OnInit {
  telegramSettings!: TelegramSettings;
  notifierSettings!: NotifierSettings;
  notificationSettings!: NotificationSettings;
  messageTemplateSettings!: MessageTemplateSettings;

  constructor(
    private changeDetector: ChangeDetectorRef,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    this.route.data.subscribe((data) => {
      const settings = data.settings as TelegramNotificationSettings;
      this.telegramSettings = pick(settings, KEYS_OF_TELEGRAM_SETTINGS);
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
