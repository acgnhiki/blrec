import { ComponentFixture, TestBed } from '@angular/core/testing';

import { OutdirEditDialogComponent } from './outdir-edit-dialog.component';

describe('OutdirEditDialogComponent', () => {
  let component: OutdirEditDialogComponent;
  let fixture: ComponentFixture<OutdirEditDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ OutdirEditDialogComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(OutdirEditDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
