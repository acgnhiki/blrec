import {
  Component,
  ChangeDetectionStrategy,
  Input,
  Output,
  ChangeDetectorRef,
  EventEmitter,
  OnChanges,
} from '@angular/core';
import {
  FormBuilder,
  FormControl,
  FormGroup,
  Validators,
} from '@angular/forms';
import { BASE_API_URL_DEFAULT } from '../../shared/constants/form';
import { baseUrlValidator } from '../../shared/directives/base-url-validator.directive';

@Component({
  selector: 'app-base-api-url-edit-dialog',
  templateUrl: './base-api-url-edit-dialog.component.html',
  styleUrls: ['./base-api-url-edit-dialog.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BaseApiUrlEditDialogComponent implements OnChanges {
  @Input() value = [];
  @Input() visible = false;
  @Output() visibleChange = new EventEmitter<boolean>();
  @Output() cancel = new EventEmitter<undefined>();
  @Output() confirm = new EventEmitter<string[]>();

  readonly settingsForm: FormGroup;
  readonly defaultBaseApiUrl = BASE_API_URL_DEFAULT;

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef
  ) {
    this.settingsForm = formBuilder.group({
      baseApiUrls: ['', [Validators.required, baseUrlValidator()]],
    });
  }

  get control() {
    return this.settingsForm.get('baseApiUrls') as FormControl;
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
    this.control.setValue(this.value.join('\n'));
    this.changeDetector.markForCheck();
  }

  handleCancel(): void {
    this.cancel.emit();
    this.close();
  }

  handleConfirm(): void {
    const value = this.control.value as string;
    const baseUrls = value
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => !!line);
    this.confirm.emit(baseUrls);
    this.close();
  }

  restoreDefault(): void {
    this.control.setValue(this.defaultBaseApiUrl);
  }
}
