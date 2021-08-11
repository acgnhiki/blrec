import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EmailNotificationSettingsComponent } from './email-notification-settings.component';

describe('EmailNotificationSettingsComponent', () => {
  let component: EmailNotificationSettingsComponent;
  let fixture: ComponentFixture<EmailNotificationSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ EmailNotificationSettingsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(EmailNotificationSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
