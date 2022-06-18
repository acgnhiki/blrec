import {
  Component,
  OnInit,
  OnChanges,
  ChangeDetectionStrategy,
  Input,
  Output,
  EventEmitter,
  ChangeDetectorRef,
} from '@angular/core';
import { FormBuilder, FormControl, FormGroup } from '@angular/forms';

import { NzSelectOptionInterface } from 'ng-zorro-antd/select/select.types';
import { MessageType } from 'src/app/settings/shared/setting.model';

import { CommonMessageTemplateSettings } from '../message-template-settings.component';

@Component({
  selector: 'app-message-template-edit-dialog',
  templateUrl: './message-template-edit-dialog.component.html',
  styleUrls: ['./message-template-edit-dialog.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MessageTemplateEditDialogComponent implements OnInit, OnChanges {
  @Input() value!: CommonMessageTemplateSettings;
  @Input() messageTypes: MessageType[] = [];

  @Input() title: string = '修改消息模板';
  @Input() visible: boolean = false;
  @Output() visibleChange = new EventEmitter<boolean>();
  @Output() cancel = new EventEmitter<undefined>();
  @Output() confirm = new EventEmitter<CommonMessageTemplateSettings>();

  readonly settingsForm: FormGroup;
  MESSAGE_TYPE_OPTIONS: NzSelectOptionInterface[] = [];

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef
  ) {
    this.settingsForm = formBuilder.group({
      messageType: [''],
      messageTitle: [''],
      messageContent: [''],
    });
  }

  get messageTypeControl() {
    return this.settingsForm.get('messageType') as FormControl;
  }

  get messageTitleControl() {
    return this.settingsForm.get('messageTitle') as FormControl;
  }

  get messageContentControl() {
    return this.settingsForm.get('messageContent') as FormControl;
  }

  ngOnInit(): void {
    this.MESSAGE_TYPE_OPTIONS = Array.from(new Set(this.messageTypes)).map(
      (type: MessageType) => ({
        label: type,
        value: type,
      })
    );
  }

  ngOnChanges(): void {
    this.setValue();
  }

  open(): void {
    this.setValue();
    this.setVisible(true);
  }

  close(): void {
    this.setVisible(false);
  }

  setVisible(visible: boolean): void {
    this.visible = visible;
    this.visibleChange.emit(visible);
    this.changeDetector.markForCheck();
  }

  setValue(): void {
    this.settingsForm.setValue(this.value);
    this.changeDetector.markForCheck();
  }

  handleCancel(): void {
    this.cancel.emit();
    this.close();
  }

  handleConfirm(): void {
    this.confirm.emit(this.settingsForm.value);
    this.close();
  }
}
