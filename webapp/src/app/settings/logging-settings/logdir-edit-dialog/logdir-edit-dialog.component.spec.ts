import { ComponentFixture, TestBed } from '@angular/core/testing';

import { LogdirEditDialogComponent } from './logdir-edit-dialog.component';

describe('LogdirEditDialogComponent', () => {
  let component: LogdirEditDialogComponent;
  let fixture: ComponentFixture<LogdirEditDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ LogdirEditDialogComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(LogdirEditDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
