import {
  ContentChild,
  Directive,
  HostBinding,
  HostListener,
} from '@angular/core';
import { FormControlName } from '@angular/forms';

import { NzSwitchComponent } from 'ng-zorro-antd/switch';

@Directive({
  selector: '[appSwitchActionable]',
})
export class SwitchActionableDirective {
  @ContentChild(FormControlName) directive?: FormControlName;

  @HostBinding('class.actionable')
  get actionable() {
    return this.directive?.valueAccessor instanceof NzSwitchComponent;
  }

  constructor() {}

  @HostListener('click', ['$event'])
  onClick(event: Event): void {
    if (event.target !== event.currentTarget) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();

    if (this.directive?.valueAccessor instanceof NzSwitchComponent) {
      this.directive.control.setValue(!this.directive.control.value);
    }
  }
}
