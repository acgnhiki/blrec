import {
  Component,
  ChangeDetectionStrategy,
  Input,
  OnChanges,
  Output,
  EventEmitter,
  ChangeDetectorRef,
} from '@angular/core';
import {
  AbstractControl,
  FormBuilder,
  FormGroup,
  Validators,
} from '@angular/forms';

import { WebhookSettings } from '../../shared/setting.model';

const DEFAULT_SETTINGS = {
  url: '',
  liveBegan: true,
  liveEnded: true,
  roomChange: true,
  recordingStarted: true,
  recordingFinished: true,
  recordingCancelled: true,
  videoFileCreated: true,
  videoFileCompleted: true,
  danmakuFileCreated: true,
  danmakuFileCompleted: true,
  rawDanmakuFileCreated: true,
  rawDanmakuFileCompleted: true,
  videoPostprocessingCompleted: true,
  spaceNoEnough: true,
  errorOccurred: true,
} as const;

@Component({
  selector: 'app-webhook-edit-dialog',
  templateUrl: './webhook-edit-dialog.component.html',
  styleUrls: ['./webhook-edit-dialog.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WebhookEditDialogComponent implements OnChanges {
  @Input() settings?: WebhookSettings;
  @Input() title = '标题';
  @Input() okButtonText = '确定';
  @Input() visible = false;
  @Output() visibleChange = new EventEmitter<boolean>();
  @Output() cancel = new EventEmitter<undefined>();
  @Output() confirm = new EventEmitter<WebhookSettings>();

  readonly settingsForm: FormGroup;

  allChecked = false;
  indeterminate = true;

  private checkboxControls: AbstractControl[];

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef
  ) {
    this.settingsForm = formBuilder.group({
      url: ['', [Validators.required, Validators.pattern(/^https?:\/\/.*$/)]],
      liveBegan: [''],
      liveEnded: [''],
      roomChange: [''],
      recordingStarted: [''],
      recordingFinished: [''],
      recordingCancelled: [''],
      videoFileCreated: [''],
      videoFileCompleted: [''],
      danmakuFileCreated: [''],
      danmakuFileCompleted: [''],
      rawDanmakuFileCreated: [''],
      rawDanmakuFileCompleted: [''],
      videoPostprocessingCompleted: [''],
      spaceNoEnough: [''],
      errorOccurred: [''],
    });

    this.checkboxControls = Object.entries(this.settingsForm.controls)
      .filter(([n]) => n !== 'url')
      .map(([, c]) => c);

    this.checkboxControls.forEach((c) =>
      c.valueChanges.subscribe(() => this.updateAllChecked())
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
    this.settingsForm.reset();
    this.setVisible(false);
  }

  setVisible(visible: boolean): void {
    this.visible = visible;
    this.visibleChange.emit(visible);
    this.changeDetector.markForCheck();
  }

  setValue(): void {
    if (this.settings === undefined) {
      this.settings = { ...DEFAULT_SETTINGS };
    }
    this.settingsForm.setValue(this.settings);
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

  setAllChecked(checked: boolean): void {
    this.indeterminate = false;
    this.allChecked = checked;
    this.checkboxControls.forEach((c) => c.setValue(checked));
  }

  private updateAllChecked(): void {
    const allValues = this.checkboxControls.map((c) => c.value);
    this.allChecked = allValues.every((v) => v);
    this.indeterminate = this.allChecked ? false : allValues.some((v) => v);
  }
}
