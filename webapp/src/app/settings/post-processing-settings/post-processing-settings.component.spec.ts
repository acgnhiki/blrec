import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PostProcessingSettingsComponent } from './post-processing-settings.component';

describe('PostProcessingSettingsComponent', () => {
  let component: PostProcessingSettingsComponent;
  let fixture: ComponentFixture<PostProcessingSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ PostProcessingSettingsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(PostProcessingSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
