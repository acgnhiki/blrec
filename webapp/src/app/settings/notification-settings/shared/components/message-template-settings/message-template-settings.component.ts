import {
  Component,
  ChangeDetectionStrategy,
  Input,
  ChangeDetectorRef,
  OnInit,
  OnChanges,
  SimpleChanges,
} from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';

import { tap } from 'rxjs/operators';
import { NzMessageService } from 'ng-zorro-antd/message';

import { retry } from 'src/app/shared/rx-operators';
import {
  MessageTemplateSettings,
  MessageType,
} from 'src/app/settings/shared/setting.model';
import { SettingService } from 'src/app/settings/shared/services/setting.service';

export interface CommonMessageTemplateSettings {
  messageType: string;
  messageTitle: string;
  messageContent: string;
}

@Component({
  selector: 'app-message-template-settings',
  templateUrl: './message-template-settings.component.html',
  styleUrls: ['./message-template-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MessageTemplateSettingsComponent implements OnInit, OnChanges {
  @Input() settings!: MessageTemplateSettings;
  @Input() keyOfSettings!:
    | 'emailNotification'
    | 'serverchanNotification'
    | 'pushdeerNotification'
    | 'pushplusNotification'
    | 'telegramNotification'
    | 'barkNotification';

  messageTypes!: MessageType[];
  beganMessageTemplateSettings!: CommonMessageTemplateSettings;
  endedMessageTemplateSettings!: CommonMessageTemplateSettings;
  spaceMessageTemplateSettings!: CommonMessageTemplateSettings;
  errorMessageTemplateSettings!: CommonMessageTemplateSettings;

  constructor(
    private changeDetector: ChangeDetectorRef,
    private message: NzMessageService,
    private settingService: SettingService
  ) { }

  ngOnInit(): void {
    switch (this.keyOfSettings) {
      case 'emailNotification':
        this.messageTypes = ['text', 'html'];
        break;
      case 'serverchanNotification':
        this.messageTypes = ['markdown'];
        break;
      case 'pushdeerNotification':
        this.messageTypes = ['markdown', 'text'];
        break;
      case 'pushplusNotification':
        this.messageTypes = ['markdown', 'text', 'html'];
        break;
      case 'telegramNotification':
        this.messageTypes = ['markdown', 'html'];
        break;
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    this.updateCommonSettings();
  }

  changeBeganMessageTemplateSettings(
    settings: CommonMessageTemplateSettings
  ): void {
    const settingsToChange = {
      beganMessageType: settings.messageType,
      beganMessageTitle: settings.messageTitle,
      beganMessageContent: settings.messageContent,
    };
    this.changeMessageTemplateSettings(settingsToChange).subscribe();
  }

  changeEndedMessageTemplateSettings(
    settings: CommonMessageTemplateSettings
  ): void {
    const settingsToChange = {
      endedMessageType: settings.messageType,
      endedMessageTitle: settings.messageTitle,
      endedMessageContent: settings.messageContent,
    };
    this.changeMessageTemplateSettings(settingsToChange).subscribe();
  }

  changeSpaceMessageTemplateSettings(
    settings: CommonMessageTemplateSettings
  ): void {
    const settingsToChange = {
      spaceMessageType: settings.messageType,
      spaceMessageTitle: settings.messageTitle,
      spaceMessageContent: settings.messageContent,
    };
    this.changeMessageTemplateSettings(settingsToChange).subscribe();
  }

  changeErrorMessageTemplateSettings(
    settings: CommonMessageTemplateSettings
  ): void {
    const settingsToChange = {
      errorMessageType: settings.messageType,
      errorMessageTitle: settings.messageTitle,
      errorMessageContent: settings.messageContent,
    };
    this.changeMessageTemplateSettings(settingsToChange).subscribe();
  }

  changeMessageTemplateSettings(settings: Partial<MessageTemplateSettings>) {
    return this.settingService
      .changeSettings({ [this.keyOfSettings]: settings })
      .pipe(
        retry(3, 300),
        tap(
          (settings) => {
            this.message.success('修改消息模板设置成功');
            this.settings = {
              ...this.settings,
              ...settings[this.keyOfSettings],
            };
            this.updateCommonSettings();
            this.changeDetector.markForCheck();
          },
          (error: HttpErrorResponse) => {
            this.message.error(`修改消息模板设置出错: ${error.message}`);
          }
        )
      );
  }

  private updateCommonSettings(): void {
    this.beganMessageTemplateSettings = {
      messageType: this.settings.beganMessageType,
      messageTitle: this.settings.beganMessageTitle,
      messageContent: this.settings.beganMessageContent,
    };
    this.endedMessageTemplateSettings = {
      messageType: this.settings.endedMessageType,
      messageTitle: this.settings.endedMessageTitle,
      messageContent: this.settings.endedMessageContent,
    };
    this.spaceMessageTemplateSettings = {
      messageType: this.settings.spaceMessageType,
      messageTitle: this.settings.spaceMessageTitle,
      messageContent: this.settings.spaceMessageContent,
    };
    this.errorMessageTemplateSettings = {
      messageType: this.settings.errorMessageType,
      messageTitle: this.settings.errorMessageTitle,
      messageContent: this.settings.errorMessageContent,
    };
  }
}
