import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TelegramSettingsComponent } from './telegram-settings.component';

describe('TelegramSettingsComponent', () => {
  let component: TelegramSettingsComponent;
  let fixture: ComponentFixture<TelegramSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ TelegramSettingsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(TelegramSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
