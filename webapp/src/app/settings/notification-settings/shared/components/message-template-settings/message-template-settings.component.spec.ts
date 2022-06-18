import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MessageTemplateSettingsComponent } from './message-template-settings.component';

describe('MessageTemplateSettingsComponent', () => {
  let component: MessageTemplateSettingsComponent;
  let fixture: ComponentFixture<MessageTemplateSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ MessageTemplateSettingsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(MessageTemplateSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
