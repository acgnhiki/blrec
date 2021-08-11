import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PushplusNotificationSettingsComponent } from './pushplus-notification-settings.component';

describe('PushplusNotificationSettingsComponent', () => {
  let component: PushplusNotificationSettingsComponent;
  let fixture: ComponentFixture<PushplusNotificationSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ PushplusNotificationSettingsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(PushplusNotificationSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
