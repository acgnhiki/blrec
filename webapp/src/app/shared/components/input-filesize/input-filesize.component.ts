import {
  Component,
  ChangeDetectionStrategy,
  forwardRef,
  OnInit,
} from '@angular/core';
import {
  ControlValueAccessor,
  FormBuilder,
  FormControl,
  FormGroup,
  NG_VALUE_ACCESSOR,
  Validators,
} from '@angular/forms';

import { OnChangeType, OnTouchedType } from 'ng-zorro-antd/core/types';

import { formatFilesize, parseFilesize } from '../../../shared/utils';
import { filterValueChanges } from 'src/app/settings/shared/rx-operators';

@Component({
  selector: 'app-input-filesize',
  templateUrl: './input-filesize.component.html',
  styleUrls: ['./input-filesize.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => InputFilesizeComponent),
      multi: true,
    },
  ],
})
export class InputFilesizeComponent implements OnInit, ControlValueAccessor {
  readonly formGroup: FormGroup;
  private value: number = 0;

  onChange: OnChangeType = () => {};
  onTouched: OnTouchedType = () => {};

  constructor(formBuilder: FormBuilder) {
    this.formGroup = formBuilder.group({
      filesize: [
        '',
        [
          Validators.required,
          Validators.pattern(/^\d{1,3}(?:\.\d{1,2})?\s?[GMK]?B$/),
        ],
      ],
    });
  }

  get filesizeControl() {
    return this.formGroup.get('filesize') as FormControl;
  }

  ngOnInit(): void {
    this.filesizeControl.valueChanges
      .pipe(filterValueChanges(this.filesizeControl))
      .subscribe((displayValue) => {
        this.onDisplayValueChange(displayValue);
      });
  }

  writeValue(value: number): void {
    this.value = value;
    this.updateDisplayValue(value);
  }

  registerOnChange(fn: OnChangeType): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: OnTouchedType): void {
    this.onTouched = fn;
  }

  setDisabledState(disabled: boolean): void {
    if (disabled) {
      this.filesizeControl.disable();
    } else {
      this.filesizeControl.enable();
    }
  }

  private onDisplayValueChange(displayValue: string): void {
    const value = parseFilesize(displayValue);
    if (typeof value === 'number' && this.value !== value) {
      this.value = value;
      this.onChange(value);
    }
  }

  private updateDisplayValue(value: number): void {
    const displayValue = formatFilesize(value);
    this.filesizeControl.setValue(displayValue);
  }
}
