import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TelegramNotificationSettingsComponent } from './telegram-notification-settings.component';

describe('TelegramNotificationSettingsComponent', () => {
  let component: TelegramNotificationSettingsComponent;
  let fixture: ComponentFixture<TelegramNotificationSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ TelegramNotificationSettingsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(TelegramNotificationSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
