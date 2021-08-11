import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RecorderSettingsComponent } from './recorder-settings.component';

describe('RecorderSettingsComponent', () => {
  let component: RecorderSettingsComponent;
  let fixture: ComponentFixture<RecorderSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ RecorderSettingsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(RecorderSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
