import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BarkNotificationSettingsComponent } from './bark-notification-settings.component';

describe('BarkNotificationSettingsComponent', () => {
  let component: BarkNotificationSettingsComponent;
  let fixture: ComponentFixture<BarkNotificationSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [BarkNotificationSettingsComponent]
    })
      .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(BarkNotificationSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
