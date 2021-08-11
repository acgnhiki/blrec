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
  ValidationErrors,
  Validators,
} from '@angular/forms';

import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import { ERRNO } from 'src/app/core/models/validation.model';
import { ValidationService } from 'src/app/core/services/validation.service';

@Component({
  selector: 'app-outdir-edit-dialog',
  templateUrl: './outdir-edit-dialog.component.html',
  styleUrls: ['./outdir-edit-dialog.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OutdirEditDialogComponent implements OnChanges {
  @Input() value = '';
  @Input() visible = false;
  @Output() visibleChange = new EventEmitter<boolean>();
  @Output() cancel = new EventEmitter<undefined>();
  @Output() confirm = new EventEmitter<string>();

  readonly settingsForm: FormGroup;

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef,
    private validationService: ValidationService
  ) {
    this.settingsForm = formBuilder.group({
      outDir: ['', [Validators.required], [this.outDirAsyncValidator]],
    });
  }

  get control() {
    return this.settingsForm.get('outDir') as FormControl;
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

  private outDirAsyncValidator = (
    control: FormControl
  ): Observable<ValidationErrors | null> => {
    return this.validationService.validateDir(control.value).pipe(
      map((result) => {
        switch (result.code) {
          case ERRNO.ENOTDIR:
            return { error: true, notADirectory: true };
          case ERRNO.EACCES:
            return { error: true, noPermissions: true };
          default:
            return null;
        }
      }),
      catchError(() => of({ error: true, failedToValidate: true }))
    );
  };
}
