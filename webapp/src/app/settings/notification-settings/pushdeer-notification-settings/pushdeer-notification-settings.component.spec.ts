import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PushdeerNotificationSettingsComponent } from './pushdeer-notification-settings.component';

describe('PushdeerNotificationSettingsComponent', () => {
  let component: PushdeerNotificationSettingsComponent;
  let fixture: ComponentFixture<PushdeerNotificationSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ PushdeerNotificationSettingsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(PushdeerNotificationSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
