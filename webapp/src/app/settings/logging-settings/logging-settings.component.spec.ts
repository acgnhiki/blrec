import { ComponentFixture, TestBed } from '@angular/core/testing';

import { LoggingSettingsComponent } from './logging-settings.component';

describe('LoggingSettingsComponent', () => {
  let component: LoggingSettingsComponent;
  let fixture: ComponentFixture<LoggingSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ LoggingSettingsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(LoggingSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
