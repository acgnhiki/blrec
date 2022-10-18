import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BarkSettingsComponent } from './bark-settings.component';

describe('BarkSettingsComponent', () => {
  let component: BarkSettingsComponent;
  let fixture: ComponentFixture<BarkSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [BarkSettingsComponent]
    })
      .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(BarkSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
