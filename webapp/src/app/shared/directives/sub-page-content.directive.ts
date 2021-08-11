import { Directive, TemplateRef } from '@angular/core';

@Directive({
  selector: '[appSubPageContent]',
})
export class SubPageContentDirective {
  constructor(public templateRef: TemplateRef<unknown>) {}
}
