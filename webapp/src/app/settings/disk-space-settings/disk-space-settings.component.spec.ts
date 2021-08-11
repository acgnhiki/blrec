import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DiskSpaceSettingsComponent } from './disk-space-settings.component';

describe('DiskSpaceSettingsComponent', () => {
  let component: DiskSpaceSettingsComponent;
  let fixture: ComponentFixture<DiskSpaceSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ DiskSpaceSettingsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(DiskSpaceSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
