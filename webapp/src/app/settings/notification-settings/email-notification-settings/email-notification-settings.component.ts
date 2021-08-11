import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
} from '@angular/core';
import { ActivatedRoute } from '@angular/router';

import pick from 'lodash-es/pick';

import {
  EmailNotificationSettings,
  EmailSettings,
  NotifierSettings,
  NotificationSettings,
  KEYS_OF_EMAIL_SETTINGS,
  KEYS_OF_NOTIFIER_SETTINGS,
  KEYS_OF_NOTIFICATION_SETTINGS,
} from '../../shared/setting.model';

@Component({
  selector: 'app-email-notification-settings',
  templateUrl: './email-notification-settings.component.html',
  styleUrls: ['./email-notification-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EmailNotificationSettingsComponent implements OnInit {
  emailSettings!: EmailSettings;
  notifierSettings!: NotifierSettings;
  notificationSettings!: NotificationSettings;

  constructor(
    private changeDetector: ChangeDetectorRef,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    this.route.data.subscribe((data) => {
      const settings = data.settings as EmailNotificationSettings;
      this.emailSettings = pick(settings, KEYS_OF_EMAIL_SETTINGS);
      this.notifierSettings = pick(settings, KEYS_OF_NOTIFIER_SETTINGS);
      this.notificationSettings = pick(settings, KEYS_OF_NOTIFICATION_SETTINGS);
      this.changeDetector.markForCheck();
    });
  }
}
