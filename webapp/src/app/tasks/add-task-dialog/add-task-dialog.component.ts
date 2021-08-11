import {
  Component,
  ChangeDetectionStrategy,
  EventEmitter,
  Input,
  Output,
  ChangeDetectorRef,
} from '@angular/core';
import {
  FormBuilder,
  FormControl,
  FormGroup,
  Validators,
} from '@angular/forms';

import { from } from 'rxjs';
import { concatMap, tap } from 'rxjs/operators';

import {
  TaskManagerService,
  AddTaskResultMessage,
} from '../shared/services/task-manager.service';

const ROOM_URL_PATTERN = /^https?:\/\/live\.bilibili\.com\/(\d+).*$/;
const INPUT_PATTERN =
  /^\s*(?:\d+(?:[ ]+\d+)*|https?:\/\/live\.bilibili\.com\/\d+.*)\s*$/;

@Component({
  selector: 'app-add-task-dialog',
  templateUrl: './add-task-dialog.component.html',
  styleUrls: ['./add-task-dialog.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AddTaskDialogComponent {
  @Input() visible = false;
  @Output() visibleChange = new EventEmitter<boolean>();

  pending = false;
  resultMessages: AddTaskResultMessage[] = [];

  readonly formGroup: FormGroup;
  readonly pattern = INPUT_PATTERN;

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef,
    private taskManager: TaskManagerService
  ) {
    this.formGroup = formBuilder.group({
      input: ['', [Validators.required, Validators.pattern(this.pattern)]],
    });
  }

  get inputControl() {
    return this.formGroup.get('input') as FormControl;
  }

  open(): void {
    this.setVisible(true);
  }

  close(): void {
    this.resultMessages = [];
    this.reset();
    this.setVisible(false);
  }

  setVisible(visible: boolean): void {
    this.visible = visible;
    this.visibleChange.emit(visible);
    this.changeDetector.markForCheck();
  }

  reset(): void {
    this.pending = false;
    this.formGroup.reset();
    this.changeDetector.markForCheck();
  }

  handleCancel(): void {
    this.close();
  }

  handleConfirm(): void {
    this.pending = true;
    const inputValue = this.inputControl.value.trim() as string;

    let roomIds: Iterable<number>;
    if (inputValue.startsWith('http')) {
      roomIds = [parseInt(ROOM_URL_PATTERN.exec(inputValue)![1])];
    } else {
      roomIds = new Set(inputValue.split(/\s+/).map((s) => parseInt(s)));
    }

    from(roomIds)
      .pipe(
        concatMap((roomId) => this.taskManager.addTask(roomId)),
        tap((resultMessage) => {
          this.resultMessages.push(resultMessage);
          this.changeDetector.markForCheck();
        })
      )
      .subscribe({
        complete: () => {
          if (this.resultMessages.every((m) => m.type === 'success')) {
            this.close();
          } else {
            this.reset();
          }
        },
      });
  }
}
