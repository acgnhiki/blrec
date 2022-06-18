import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MessageTemplateEditDialogComponent } from './message-template-edit-dialog.component';

describe('MessageTemplateEditDialogComponent', () => {
  let component: MessageTemplateEditDialogComponent;
  let fixture: ComponentFixture<MessageTemplateEditDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ MessageTemplateEditDialogComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(MessageTemplateEditDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
