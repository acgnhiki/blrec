import {
  Component,
  OnChanges,
  ChangeDetectionStrategy,
  Input,
  Output,
  EventEmitter,
  ChangeDetectorRef,
} from '@angular/core';
import {
  FormBuilder,
  FormControl,
  FormGroup,
  Validators,
} from '@angular/forms';
import {
  PATH_TEMPLATE_DEFAULT,
  PATH_TEMPLATE_PATTERN,
  PATH_TEMPLATE_VARIABLES,
} from '../../shared/constants/form';

@Component({
  selector: 'app-path-template-edit-dialog',
  templateUrl: './path-template-edit-dialog.component.html',
  styleUrls: ['./path-template-edit-dialog.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PathTemplateEditDialogComponent implements OnChanges {
  @Input() value = '';
  @Input() visible = false;
  @Output() visibleChange = new EventEmitter<boolean>();
  @Output() cancel = new EventEmitter<undefined>();
  @Output() confirm = new EventEmitter<string>();

  readonly settingsForm: FormGroup;
  readonly pathTemplatePattern = PATH_TEMPLATE_PATTERN;
  readonly pathTemplateDefault = PATH_TEMPLATE_DEFAULT;
  readonly pathTemplateVariables = PATH_TEMPLATE_VARIABLES;

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef
  ) {
    this.settingsForm = formBuilder.group({
      pathTemplate: [
        '',
        [Validators.required, Validators.pattern(this.pathTemplatePattern)],
      ],
    });
  }

  get control() {
    return this.settingsForm.get('pathTemplate') as FormControl;
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
    this.control.setValue(this.value);
    this.changeDetector.markForCheck();
  }

  handleCancel(): void {
    this.cancel.emit();
    this.close();
  }

  handleConfirm(): void {
    this.confirm.emit(this.control.value.trim());
    this.close();
  }

  restoreDefault(): void {
    this.control.setValue(this.pathTemplateDefault);
  }
}
