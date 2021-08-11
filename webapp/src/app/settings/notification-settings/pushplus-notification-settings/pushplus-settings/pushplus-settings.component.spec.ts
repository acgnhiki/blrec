import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PushplusSettingsComponent } from './pushplus-settings.component';

describe('PushplusSettingsComponent', () => {
  let component: PushplusSettingsComponent;
  let fixture: ComponentFixture<PushplusSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ PushplusSettingsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(PushplusSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
