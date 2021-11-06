import {
  Component,
  ChangeDetectionStrategy,
  Input,
  ContentChild,
} from '@angular/core';

import { SubPageContentDirective } from '../../directives/sub-page-content.directive';

@Component({
  selector: 'app-sub-page',
  templateUrl: './sub-page.component.html',
  styleUrls: ['./sub-page.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SubPageComponent {
  @Input() pageTitle = '';
  @Input() loading = false;
  @Input() pageStyles = {};
  @Input() contentStyles = {};

  @ContentChild(SubPageContentDirective)
  content?: SubPageContentDirective;
}
