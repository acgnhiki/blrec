import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ServerchanSettingsComponent } from './serverchan-settings.component';

describe('ServerchanSettingsComponent', () => {
  let component: ServerchanSettingsComponent;
  let fixture: ComponentFixture<ServerchanSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ServerchanSettingsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ServerchanSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
