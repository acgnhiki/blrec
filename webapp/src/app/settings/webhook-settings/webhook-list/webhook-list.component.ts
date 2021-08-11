import {
  Component,
  ChangeDetectionStrategy,
  Input,
  Output,
  EventEmitter,
} from '@angular/core';

import { WebhookSettings } from '../../shared/setting.model';

@Component({
  selector: 'app-webhook-list',
  templateUrl: './webhook-list.component.html',
  styleUrls: ['./webhook-list.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WebhookListComponent {
  @Input() data!: WebhookSettings[];
  @Input() header = '';
  @Input() addable = true;
  @Input() clearable = true;

  @Output() add = new EventEmitter<undefined>();
  @Output() edit = new EventEmitter<number>();
  @Output() remove = new EventEmitter<number>();
  @Output() clear = new EventEmitter<undefined>();
}
