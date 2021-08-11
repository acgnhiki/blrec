import { ComponentFixture, TestBed } from '@angular/core/testing';

import { OutputSettingsComponent } from './output-settings.component';

describe('OutputSettingsComponent', () => {
  let component: OutputSettingsComponent;
  let fixture: ComponentFixture<OutputSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ OutputSettingsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(OutputSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
