import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ServerchanNotificationSettingsComponent } from './serverchan-notification-settings.component';

describe('ServerchanNotificationSettingsComponent', () => {
  let component: ServerchanNotificationSettingsComponent;
  let fixture: ComponentFixture<ServerchanNotificationSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ServerchanNotificationSettingsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ServerchanNotificationSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
